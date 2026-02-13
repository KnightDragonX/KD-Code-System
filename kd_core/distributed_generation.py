"""
Cloud-Based Distributed KD-Code Generation Service
Implements a scalable, distributed system for generating KD-Codes across multiple nodes
"""

import asyncio
import aiohttp
import json
import base64
import hashlib
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import redis
import uuid
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp
from functools import partial


class NodeType(Enum):
    """Enumeration of node types in the distributed system"""
    GENERATOR = "generator"
    SCANNER = "scanner"
    VALIDATOR = "validator"
    STORAGE = "storage"


@dataclass
class NodeInfo:
    """Information about a node in the distributed system"""
    node_id: str
    node_type: NodeType
    host: str
    port: int
    status: str
    last_seen: float
    capacity: int
    load: int


@dataclass
class GenerationTask:
    """Represents a KD-Code generation task"""
    task_id: str
    text: str
    parameters: Dict[str, Any]
    priority: int
    created_at: float
    assigned_node: Optional[str] = None
    status: str = "pending"


class DistributedKDGenerator:
    """
    Cloud-based distributed KD-Code generation service
    """
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0):
        """Initialize the distributed generation service"""
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
        self.nodes: Dict[str, NodeInfo] = {}
        self.task_queue = "kd_generation_tasks"
        self.result_queue = "kd_generation_results"
        self.node_registry = "kd_nodes"
        self.heartbeat_interval = 30  # seconds
        self.max_workers = min(32, (mp.cpu_count() or 1) + 4)  # Standard Python practice
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Initialize Redis structures
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis structures for the distributed system"""
        # Create sorted set for task priorities
        if not self.redis_client.exists(f"{self.task_queue}:priorities"):
            self.redis_client.zadd(f"{self.task_queue}:priorities", {})
        
        # Create hash for storing task details
        if not self.redis_client.exists(f"{self.task_queue}:details"):
            self.redis_client.hset(f"{self.task_queue}:details", "placeholder", "{}")
            self.redis_client.hdel(f"{self.task_queue}:details", "placeholder")
    
    def register_node(self, node_type: NodeType, host: str, port: int, capacity: int = 10) -> str:
        """
        Register a new node in the distributed system
        
        Args:
            node_type: Type of node (generator, scanner, etc.)
            host: Host address of the node
            port: Port of the node
            capacity: Processing capacity of the node
        
        Returns:
            Node ID
        """
        node_id = str(uuid.uuid4())
        node_info = NodeInfo(
            node_id=node_id,
            node_type=node_type,
            host=host,
            port=port,
            status="active",
            last_seen=time.time(),
            capacity=capacity,
            load=0
        )
        
        # Store node info in Redis
        node_key = f"{self.node_registry}:{node_id}"
        self.redis_client.hmset(node_key, {
            'node_id': node_info.node_id,
            'node_type': node_info.node_type.value,
            'host': node_info.host,
            'port': str(node_info.port),
            'status': node_info.status,
            'last_seen': str(node_info.last_seen),
            'capacity': str(node_info.capacity),
            'load': str(node_info.load)
        })
        self.redis_client.expire(node_key, 3600)  # Expire after 1 hour
        
        # Add to node registry
        self.redis_client.sadd(self.node_registry, node_id)
        
        # Update local cache
        self.nodes[node_id] = node_info
        
        return node_id
    
    def submit_generation_task(self, text: str, parameters: Dict[str, Any] = None, priority: int = 5) -> str:
        """
        Submit a KD-Code generation task to the distributed system
        
        Args:
            text: Text to encode in the KD-Code
            parameters: Additional parameters for generation
            priority: Priority of the task (1-10, 10 is highest)
        
        Returns:
            Task ID
        """
        if parameters is None:
            parameters = {}
        
        task_id = str(uuid.uuid4())
        task = GenerationTask(
            task_id=task_id,
            text=text,
            parameters=parameters,
            priority=priority,
            created_at=time.time()
        )
        
        # Serialize task
        task_data = {
            'task_id': task.task_id,
            'text': task.text,
            'parameters': json.dumps(task.parameters),
            'priority': task.priority,
            'created_at': task.created_at,
            'assigned_node': task.assigned_node,
            'status': task.status
        }
        
        # Add to task queue with priority scoring
        self.redis_client.zadd(f"{self.task_queue}:priorities", {task_id: 10 - priority})  # Higher priority = lower score
        self.redis_client.hset(f"{self.task_queue}:details", task_id, json.dumps(task_data))
        
        return task_id
    
    def get_available_generator_node(self) -> Optional[NodeInfo]:
        """
        Get an available generator node with lowest load
        
        Returns:
            Available node info or None if no nodes available
        """
        # Get all active generator nodes
        node_ids = self.redis_client.smembers(self.node_registry)
        available_nodes = []
        
        for node_id in node_ids:
            node_key = f"{self.node_registry}:{node_id}"
            node_data = self.redis_client.hgetall(node_key)
            
            if node_data and node_data.get('node_type') == NodeType.GENERATOR.value and node_data.get('status') == 'active':
                # Calculate load ratio
                capacity = int(node_data.get('capacity', 1))
                load = int(node_data.get('load', 0))
                load_ratio = load / capacity if capacity > 0 else 0
                
                # Only consider nodes with capacity
                if load < capacity:
                    node_info = NodeInfo(
                        node_id=node_data['node_id'],
                        node_type=NodeType(node_data['node_type']),
                        host=node_data['host'],
                        port=int(node_data['port']),
                        status=node_data['status'],
                        last_seen=float(node_data['last_seen']),
                        capacity=capacity,
                        load=load
                    )
                    available_nodes.append((node_info, load_ratio))
        
        # Return node with lowest load ratio
        if available_nodes:
            available_nodes.sort(key=lambda x: x[1])  # Sort by load ratio
            return available_nodes[0][0]
        
        return None
    
    async def process_generation_tasks(self):
        """Asynchronously process generation tasks in the queue"""
        while True:
            try:
                # Get highest priority task
                task_ids = self.redis_client.zrange(f"{self.task_queue}:priorities", 0, 0, withscores=True)
                
                if not task_ids:
                    # No tasks, sleep briefly
                    await asyncio.sleep(0.1)
                    continue
                
                task_id, priority = task_ids[0]
                
                # Get task details
                task_details_json = self.redis_client.hget(f"{self.task_queue}:details", task_id)
                if not task_details_json:
                    # Task was removed, continue
                    continue
                
                task_details = json.loads(task_details_json)
                
                # Check if task is already assigned
                if task_details.get('assigned_node'):
                    # Task is already assigned, continue to next
                    await asyncio.sleep(0.1)
                    continue
                
                # Find available generator node
                node_info = self.get_available_generator_node()
                if not node_info:
                    # No available nodes, wait and retry
                    await asyncio.sleep(1)
                    continue
                
                # Assign task to node
                task_details['assigned_node'] = node_info.node_id
                task_details['status'] = 'assigned'
                self.redis_client.hset(f"{self.task_queue}:details", task_id, json.dumps(task_details))
                
                # Increment node load
                node_key = f"{self.node_registry}:{node_info.node_id}"
                current_load = int(self.redis_client.hget(node_key, 'load') or 0)
                self.redis_client.hincrby(node_key, 'load', 1)
                
                # Send task to node (in a real implementation, this would be an HTTP request)
                await self._send_task_to_node(task_details, node_info)
                
            except Exception as e:
                print(f"Error processing generation tasks: {e}")
                await asyncio.sleep(1)
    
    async def _send_task_to_node(self, task_details: Dict[str, Any], node_info: NodeInfo):
        """Send a task to a specific node for processing"""
        # In a real implementation, this would make an HTTP request to the node
        # For now, we'll simulate the process
        
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        # In a real system, we would:
        # 1. Send an HTTP request to the node with task details
        # 2. Receive the result
        # 3. Store the result in the result queue
        # 4. Update task status to completed
        # 5. Decrement node load
        
        # For simulation, we'll just mark as completed
        task_id = task_details['task_id']
        self.redis_client.hset(f"{self.task_queue}:details", task_id, 
                              json.dumps({**task_details, 'status': 'completed'}))
        
        # Decrement node load
        node_key = f"{self.node_registry}:{node_info.node_id}"
        self.redis_client.hincrby(node_key, 'load', -1)
        
        # Add simulated result
        # In real implementation, this would come from the node
        result = {
            'task_id': task_id,
            'result': 'simulated_kd_code_image_data',
            'status': 'success',
            'processed_at': time.time()
        }
        self.redis_client.lpush(self.result_queue, json.dumps(result))
    
    def get_task_result(self, task_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        Get the result of a generation task
        
        Args:
            task_id: ID of the task
            timeout: Timeout in seconds
        
        Returns:
            Task result or None if not found/timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check if result is available
            results = self.redis_client.lrange(self.result_queue, 0, -1)
            
            for result_json in results:
                result = json.loads(result_json)
                if result.get('task_id') == task_id:
                    # Remove from queue and return
                    self.redis_client.lrem(self.result_queue, 1, result_json)
                    return result
            
            # Brief pause before checking again
            time.sleep(0.1)
        
        return None
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """
        Get the status of the entire cluster
        
        Returns:
            Cluster status information
        """
        node_ids = self.redis_client.smembers(self.node_registry)
        nodes_status = []
        
        total_capacity = 0
        total_load = 0
        
        for node_id in node_ids:
            node_key = f"{self.node_registry}:{node_id}"
            node_data = self.redis_client.hgetall(node_key)
            
            if node_data:
                node_status = {
                    'node_id': node_data['node_id'],
                    'node_type': node_data['node_type'],
                    'host': node_data['host'],
                    'port': int(node_data['port']),
                    'status': node_data['status'],
                    'capacity': int(node_data['capacity']),
                    'load': int(node_data['load']),
                    'last_seen': float(node_data['last_seen'])
                }
                
                total_capacity += int(node_data['capacity'])
                total_load += int(node_data['load'])
                
                nodes_status.append(node_status)
        
        # Get task queue status
        pending_tasks = self.redis_client.zcard(f"{self.task_queue}:priorities")
        
        return {
            'nodes': nodes_status,
            'total_nodes': len(nodes_status),
            'total_capacity': total_capacity,
            'total_load': total_load,
            'utilization': total_load / total_capacity if total_capacity > 0 else 0,
            'pending_tasks': pending_tasks,
            'timestamp': time.time()
        }
    
    def heartbeat_monitor(self):
        """Monitor node heartbeats and remove inactive nodes"""
        while True:
            try:
                node_ids = self.redis_client.smembers(self.node_registry)
                current_time = time.time()
                
                for node_id in node_ids:
                    node_key = f"{self.node_registry}:{node_id}"
                    last_seen = self.redis_client.hget(node_key, 'last_seen')
                    
                    if last_seen and current_time - float(last_seen) > self.heartbeat_interval * 2:
                        # Node is inactive, mark as offline
                        self.redis_client.hset(node_key, 'status', 'inactive')
                        print(f"Node {node_id} marked as inactive due to missed heartbeat")
                
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                print(f"Error in heartbeat monitor: {e}")
                time.sleep(self.heartbeat_interval)


# Global distributed generator instance
distributed_generator = DistributedKDGenerator()


def initialize_distributed_service(redis_host='localhost', redis_port=6379):
    """Initialize the distributed KD-Code generation service"""
    global distributed_generator
    distributed_generator = DistributedKDGenerator(redis_host, redis_port)


def submit_generation_request(text: str, params: Dict[str, Any] = None, priority: int = 5) -> str:
    """Submit a generation request to the distributed system"""
    return distributed_generator.submit_generation_task(text, params, priority)


def get_generation_result(task_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """Get the result of a generation task"""
    return distributed_generator.get_task_result(task_id, timeout)


def get_cluster_status() -> Dict[str, Any]:
    """Get the status of the distributed cluster"""
    return distributed_generator.get_cluster_status()


# Example usage
if __name__ == "__main__":
    # Initialize the distributed service
    initialize_distributed_service()
    
    # Register a local generator node
    node_id = distributed_generator.register_node(
        node_type=NodeType.GENERATOR,
        host="localhost",
        port=5000,
        capacity=20
    )
    print(f"Registered node: {node_id}")
    
    # Submit a generation task
    task_id = submit_generation_request(
        "Hello from distributed system!",
        params={
            'segments_per_ring': 16,
            'anchor_radius': 10,
            'ring_width': 15,
            'scale_factor': 5
        },
        priority=8
    )
    print(f"Submitted task: {task_id}")
    
    # Get cluster status
    status = get_cluster_status()
    print(f"Cluster status: {status}")
    
    # In a real application, you would run the task processor
    # asyncio.run(distributed_generator.process_generation_tasks())