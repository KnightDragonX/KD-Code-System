"""
3D Printable KD-Code Generator
Creates 3D models of KD-Codes that can be printed physically
"""

import numpy as np
import math
from typing import Tuple, Dict, Any, List
import json
from kd_core.encoder import generate_kd_code
from kd_core.config import (
    DEFAULT_SEGMENTS_PER_RING, DEFAULT_ANCHOR_RADIUS, DEFAULT_RING_WIDTH,
    DEFAULT_SCALE_FACTOR, DEFAULT_MAX_CHARS
)


class KDCode3DGenerator:
    """
    Generates 3D models of KD-Codes for physical printing
    """
    
    def __init__(self):
        self.default_height = 2.0  # mm
        self.default_base_thickness = 1.0  # mm
        self.default_material_density = 1.0  # g/cm³ (PLA density as default)
        self.layer_height = 0.2  # mm for 3D printing
    
    def generate_3d_model(self, text: str, 
                         segments_per_ring: int = DEFAULT_SEGMENTS_PER_RING,
                         anchor_radius: int = DEFAULT_ANCHOR_RADIUS,
                         ring_width: int = DEFAULT_RING_WIDTH,
                         scale_factor: int = DEFAULT_SCALE_FACTOR,
                         height: float = 2.0,
                         base_thickness: float = 1.0,
                         output_format: str = 'stl') -> Dict[str, Any]:
        """
        Generate a 3D model of a KD-Code
        
        Args:
            text: Text to encode in the KD-Code
            segments_per_ring: Number of segments per ring
            anchor_radius: Radius of the central anchor
            ring_width: Width of each ring
            scale_factor: Scale factor for the model
            height: Height of the raised elements (mm)
            base_thickness: Thickness of the base plate (mm)
            output_format: Output format ('stl', 'obj', 'gltf', 'json')
        
        Returns:
            Dictionary containing the 3D model data and metadata
        """
        # First, generate the 2D KD-Code to get the bit pattern
        # For 3D, we'll create a simplified version that extracts the pattern
        bit_pattern = self._text_to_bit_pattern(text)
        
        # Calculate dimensions based on parameters
        rings_needed = math.ceil(len(bit_pattern) / segments_per_ring)
        outer_radius = anchor_radius + rings_needed * ring_width + ring_width  # Extra for outer ring
        
        # Generate the 3D geometry
        vertices, faces = self._create_3d_geometry(
            bit_pattern, 
            segments_per_ring, 
            rings_needed, 
            anchor_radius, 
            ring_width, 
            height, 
            base_thickness
        )
        
        # Create model based on requested format
        if output_format.lower() == 'stl':
            model_data = self._create_stl_format(vertices, faces)
        elif output_format.lower() == 'obj':
            model_data = self._create_obj_format(vertices, faces)
        elif output_format.lower() == 'gltf':
            model_data = self._create_gltf_format(vertices, faces)
        else:  # Default to JSON
            model_data = self._create_json_format(vertices, faces)
        
        return {
            'model': model_data,
            'format': output_format,
            'dimensions': {
                'diameter': outer_radius * 2 * scale_factor,
                'height': height + base_thickness,
                'layers': int((height + base_thickness) / self.layer_height)
            },
            'estimated_print_time': self._estimate_print_time(outer_radius, height, base_thickness),
            'estimated_material_usage': self._estimate_material_usage(outer_radius, height, base_thickness),
            'metadata': {
                'encoded_text': text,
                'segments_per_ring': segments_per_ring,
                'anchor_radius': anchor_radius,
                'ring_width': ring_width,
                'scale_factor': scale_factor
            }
        }
    
    def _text_to_bit_pattern(self, text: str) -> List[int]:
        """
        Convert text to a bit pattern similar to the encoder
        """
        bit_pattern = []
        for char in text:
            # Convert each character to its ASCII value and then to 8-bit binary
            ascii_val = ord(char)
            binary = format(ascii_val, '08b')  # 8-bit binary representation
            for bit in binary:
                bit_pattern.append(int(bit))
        
        return bit_pattern
    
    def _create_3d_geometry(self, bit_pattern: List[int], 
                           segments_per_ring: int, 
                           rings_needed: int,
                           anchor_radius: int,
                           ring_width: int,
                           height: float,
                           base_thickness: float) -> Tuple[List, List]:
        """
        Create 3D geometry for the KD-Code
        
        Returns:
            Tuple of (vertices, faces) for the 3D model
        """
        vertices = []
        faces = []
        
        # Calculate total radius needed
        outer_radius = anchor_radius + rings_needed * ring_width
        
        # Create base disc
        base_vertices, base_faces = self._create_base_disc(outer_radius, base_thickness)
        vertices.extend(base_vertices)
        faces.extend(base_faces)
        
        # Offset for the raised pattern on top of the base
        vertex_offset = len(base_vertices)
        
        # Create the anchor (central circle)
        anchor_vertices, anchor_faces = self._create_raised_cylinder(
            0, 0, anchor_radius, height, vertex_offset
        )
        vertices.extend(anchor_vertices)
        faces.extend(anchor_faces)
        vertex_offset = len(vertices)
        
        # Create data rings with raised segments for 1-bits
        bit_idx = 0
        for ring_idx in range(rings_needed):
            ring_radius = anchor_radius + ring_idx * ring_width + ring_width / 2  # Middle of ring
            
            for seg_idx in range(segments_per_ring):
                if bit_idx < len(bit_pattern):
                    bit = bit_pattern[bit_idx]
                    
                    if bit == 1:  # Only create raised segment for 1-bits
                        # Calculate position of this segment
                        angle = 2 * math.pi * seg_idx / segments_per_ring
                        
                        # Create a small rectangular prism for this segment
                        seg_vertices, seg_faces = self._create_raised_segment(
                            ring_radius, angle, ring_width/2, height, vertex_offset
                        )
                        
                        vertices.extend(seg_vertices)
                        faces.extend(seg_faces)
                        vertex_offset = len(vertices)
                    
                    bit_idx += 1
        
        # Create orientation fin (raised triangle at top)
        fin_vertices, fin_faces = self._create_orientation_fin(
            0, -(anchor_radius + ring_width/2), 2, 4, height, vertex_offset
        )
        vertices.extend(fin_vertices)
        faces.extend(fin_faces)
        
        return vertices, faces
    
    def _create_base_disc(self, radius: float, thickness: float) -> Tuple[List, List]:
        """
        Create a flat base disc for the KD-Code
        
        Returns:
            Tuple of (vertices, faces) for the base disc
        """
        vertices = []
        faces = []
        
        # Create center vertex
        center_z = 0
        center_idx = len(vertices)
        vertices.append([0, 0, center_z])
        
        # Create vertices around the circumference
        num_segments = 64  # Higher number = smoother circle
        for i in range(num_segments):
            angle = 2 * math.pi * i / num_segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            vertices.append([x, y, center_z])
        
        # Create triangles forming the disc
        for i in range(num_segments):
            v1 = center_idx  # Center vertex
            v2 = 1 + i  # Current vertex
            v3 = 1 + (i + 1) % num_segments  # Next vertex
            
            faces.append([v1, v2, v3])
        
        # Create top face (raised surface)
        top_center_idx = len(vertices)
        vertices.append([0, 0, thickness])
        
        for i in range(num_segments):
            angle = 2 * math.pi * i / num_segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            vertices.append([x, y, thickness])
        
        # Create triangles for top face
        for i in range(num_segments):
            v1 = top_center_idx  # Top center vertex
            v2 = top_center_idx + 1 + i  # Current top vertex
            v3 = top_center_idx + 1 + (i + 1) % num_segments  # Next top vertex
            
            faces.append([v1, v3, v2])  # Reversed winding for correct normals
        
        # Create sides (connecting walls)
        for i in range(num_segments):
            idx1 = 1 + i
            idx2 = 1 + (i + 1) % num_segments
            idx3 = top_center_idx + 1 + i
            idx4 = top_center_idx + 1 + (i + 1) % num_segments
            
            # Side face 1
            faces.append([idx1, idx2, idx4])
            faces.append([idx1, idx4, idx3])
        
        return vertices, faces
    
    def _create_raised_cylinder(self, x: float, y: float, radius: float, height: float, 
                               vertex_offset: int = 0) -> Tuple[List, List]:
        """
        Create a raised cylinder (for anchor)
        
        Returns:
            Tuple of (vertices, faces) for the cylinder
        """
        vertices = []
        faces = []
        
        # Create bottom circle
        num_segments = 32
        bottom_center_idx = len(vertices)
        vertices.append([x, y, 0])
        
        for i in range(num_segments):
            angle = 2 * math.pi * i / num_segments
            vx = x + radius * math.cos(angle)
            vy = y + radius * math.sin(angle)
            vz = 0
            vertices.append([vx, vy, vz])
        
        # Bottom face triangles
        for i in range(num_segments):
            v1 = bottom_center_idx
            v2 = bottom_center_idx + 1 + i
            v3 = bottom_center_idx + 1 + (i + 1) % num_segments
            faces.append([v1, v3, v2])
        
        # Create top circle
        top_center_idx = len(vertices)
        vertices.append([x, y, height])
        
        for i in range(num_segments):
            angle = 2 * math.pi * i / num_segments
            vx = x + radius * math.cos(angle)
            vy = y + radius * math.sin(angle)
            vz = height
            vertices.append([vx, vy, vz])
        
        # Top face triangles
        for i in range(num_segments):
            v1 = top_center_idx
            v2 = top_center_idx + 1 + i
            v3 = top_center_idx + 1 + (i + 1) % num_segments
            faces.append([v1, v2, v3])
        
        # Side faces
        for i in range(num_segments):
            idx1 = bottom_center_idx + 1 + i
            idx2 = bottom_center_idx + 1 + (i + 1) % num_segments
            idx3 = top_center_idx + 1 + i
            idx4 = top_center_idx + 1 + (i + 1) % num_segments
            
            faces.append([idx1, idx2, idx4])
            faces.append([idx1, idx4, idx3])
        
        # Apply vertex offset
        if vertex_offset > 0:
            faces = [[v + vertex_offset for v in face] for face in faces]
        
        return vertices, faces
    
    def _create_raised_segment(self, radius: float, angle: float, width: float, 
                              height: float, vertex_offset: int = 0) -> Tuple[List, List]:
        """
        Create a raised rectangular segment for a data bit
        
        Returns:
            Tuple of (vertices, faces) for the segment
        """
        vertices = []
        faces = []
        
        # Calculate the inner and outer radii for this segment
        inner_radius = radius - width/2
        outer_radius = radius + width/2
        
        # Calculate angle span for this segment (assume equal distribution)
        angle_span = 2 * math.pi / 32  # Using 32 segments per full circle as example
        half_angle = angle_span / 2
        
        # Define the 4 corners of the segment at the base
        corners = [
            [inner_radius * math.cos(angle - half_angle), inner_radius * math.sin(angle - half_angle), 0],
            [outer_radius * math.cos(angle - half_angle), outer_radius * math.sin(angle - half_angle), 0],
            [outer_radius * math.cos(angle + half_angle), outer_radius * math.sin(angle + half_angle), 0],
            [inner_radius * math.cos(angle + half_angle), inner_radius * math.sin(angle + half_angle), 0]
        ]
        
        # Add bottom face vertices
        for corner in corners:
            vertices.append(corner)
        
        # Add top face vertices
        for corner in corners:
            vertices.append([corner[0], corner[1], height])
        
        # Define faces (using 0-indexed local to this segment)
        # Bottom face
        faces.append([0, 3, 2, 1])
        
        # Top face
        faces.append([4, 5, 6, 7])
        
        # Side faces
        faces.append([0, 1, 5, 4])  # Side 1
        faces.append([1, 2, 6, 5])  # Side 2
        faces.append([2, 3, 7, 6])  # Side 3
        faces.append([3, 0, 4, 7])  # Side 4
        
        # Apply vertex offset
        if vertex_offset > 0:
            faces = [[v + vertex_offset for v in face] for face in faces]
        
        return vertices, faces
    
    def _create_orientation_fin(self, x: float, y: float, width: float, length: float, 
                               height: float, vertex_offset: int = 0) -> Tuple[List, List]:
        """
        Create a raised orientation fin (triangular shape)
        
        Returns:
            Tuple of (vertices, faces) for the orientation fin
        """
        vertices = []
        faces = []
        
        # Define the 3 corners of the triangle at the base
        corners = [
            [x, y, 0],  # Tip of triangle
            [x - width/2, y + length, 0],  # Bottom left
            [x + width/2, y + length, 0]   # Bottom right
        ]
        
        # Add bottom face vertices
        for corner in corners:
            vertices.append(corner)
        
        # Add top face vertices
        for corner in corners:
            vertices.append([corner[0], corner[1], height])
        
        # Define faces (using 0-indexed local to this fin)
        # Bottom face
        faces.append([0, 1, 2])
        
        # Top face
        faces.append([3, 5, 4])
        
        # Side faces
        faces.append([0, 1, 4, 3])  # Side 1
        faces.append([1, 2, 5, 4])  # Side 2
        faces.append([2, 0, 3, 5])  # Side 3
        
        # Apply vertex offset
        if vertex_offset > 0:
            faces = [[v + vertex_offset for v in face] for face in faces]
        
        return vertices, faces
    
    def _create_stl_format(self, vertices: List, faces: List) -> str:
        """
        Create STL format string from vertices and faces
        
        Returns:
            STL format string
        """
        stl_content = "solid kd_code\n"
        
        for face in faces:
            if len(face) == 3:  # Triangle
                v1 = vertices[face[0]]
                v2 = vertices[face[1]]
                v3 = vertices[face[2]]
                
                # Calculate normal (simplified - using first vertex as reference)
                # In a real implementation, we would properly calculate the face normal
                normal = [0, 0, 1]  # Simplified normal pointing up
                
                stl_content += f"  facet normal {normal[0]} {normal[1]} {normal[2]}\n"
                stl_content += "    outer loop\n"
                stl_content += f"      vertex {v1[0]} {v1[1]} {v1[2]}\n"
                stl_content += f"      vertex {v2[0]} {v2[1]} {v2[2]}\n"
                stl_content += f"      vertex {v3[0]} {v3[1]} {v3[2]}\n"
                stl_content += "    endloop\n"
                stl_content += "  endfacet\n"
            elif len(face) == 4:  # Quad, break into two triangles
                v1 = vertices[face[0]]
                v2 = vertices[face[1]]
                v3 = vertices[face[2]]
                v4 = vertices[face[3]]
                
                # First triangle
                normal = [0, 0, 1]
                stl_content += f"  facet normal {normal[0]} {normal[1]} {normal[2]}\n"
                stl_content += "    outer loop\n"
                stl_content += f"      vertex {v1[0]} {v1[1]} {v1[2]}\n"
                stl_content += f"      vertex {v2[0]} {v2[1]} {v2[2]}\n"
                stl_content += f"      vertex {v3[0]} {v3[1]} {v3[2]}\n"
                stl_content += "    endloop\n"
                stl_content += "  endfacet\n"
                
                # Second triangle
                stl_content += f"  facet normal {normal[0]} {normal[1]} {normal[2]}\n"
                stl_content += "    outer loop\n"
                stl_content += f"      vertex {v1[0]} {v1[1]} {v1[2]}\n"
                stl_content += f"      vertex {v3[0]} {v3[1]} {v3[2]}\n"
                stl_content += f"      vertex {v4[0]} {v4[1]} {v4[2]}\n"
                stl_content += "    endloop\n"
                stl_content += "  endfacet\n"
        
        stl_content += "endsolid kd_code\n"
        return stl_content
    
    def _create_obj_format(self, vertices: List, faces: List) -> str:
        """
        Create OBJ format string from vertices and faces
        
        Returns:
            OBJ format string
        """
        obj_content = "# KD-Code 3D Model\n"
        
        # Write vertices
        for v in vertices:
            obj_content += f"v {v[0]} {v[1]} {v[2]}\n"
        
        # Write texture coordinates (simplified)
        obj_content += "# Texture coordinates\n"
        for v in vertices:
            obj_content += f"vt {v[0]/100} {v[1]/100}\n"
        
        # Write normals (simplified)
        obj_content += "# Normals\n"
        obj_content += "vn 0 0 1\n"
        
        # Write faces
        obj_content += "# Faces\n"
        for face in faces:
            if len(face) == 3:  # Triangle
                obj_content += f"f {face[0]+1}/{face[0]+1}/1 {face[1]+1}/{face[1]+1}/1 {face[2]+1}/{face[2]+1}/1\n"
            elif len(face) == 4:  # Quad
                obj_content += f"f {face[0]+1}/{face[0]+1}/1 {face[1]+1}/{face[1]+1}/1 {face[2]+1}/{face[2]+1}/1 {face[3]+1}/{face[3]+1}/1\n"
        
        return obj_content
    
    def _create_gltf_format(self, vertices: List, faces: List) -> Dict:
        """
        Create GLTF format dictionary from vertices and faces
        
        Returns:
            GLTF format dictionary
        """
        import base64
        
        # Convert vertices and faces to binary buffers
        vertex_data = []
        for v in vertices:
            vertex_data.extend(v)
        
        face_data = []
        for face in faces:
            if len(face) == 3:  # Triangle
                face_data.extend(face)
            elif len(face) == 4:  # Quad, triangulate
                face_data.extend([face[0], face[1], face[2]])  # First triangle
                face_data.extend([face[0], face[2], face[3]])  # Second triangle
        
        # Create a simple GLTF structure
        gltf = {
            "asset": {
                "version": "2.0",
                "generator": "KD-Code 3D Generator"
            },
            "scenes": [{
                "nodes": [0]
            }],
            "nodes": [{
                "mesh": 0
            }],
            "meshes": [{
                "primitives": [{
                    "attributes": {
                        "POSITION": 0
                    },
                    "indices": 1
                }]
            }],
            "accessors": [
                {
                    "bufferView": 0,
                    "componentType": 5126,  # FLOAT
                    "count": len(vertices),
                    "type": "VEC3",
                    "max": [max(v[0] for v in vertices), max(v[1] for v in vertices), max(v[2] for v in vertices)],
                    "min": [min(v[0] for v in vertices), min(v[1] for v in vertices), min(v[2] for v in vertices)]
                },
                {
                    "bufferView": 1,
                    "componentType": 5123,  # UNSIGNED_SHORT
                    "count": len(face_data),
                    "type": "SCALAR"
                }
            ],
            "bufferViews": [
                {
                    "buffer": 0,
                    "byteOffset": 0,
                    "byteLength": len(vertex_data) * 4,  # 4 bytes per float
                    "target": 34962  # ARRAY_BUFFER
                },
                {
                    "buffer": 0,
                    "byteOffset": len(vertex_data) * 4,
                    "byteLength": len(face_data) * 2,  # 2 bytes per unsigned short
                    "target": 34963  # ELEMENT_ARRAY_BUFFER
                }
            ],
            "buffers": [{
                "uri": "data:application/octet-stream;base64," + base64.b64encode(self._create_binary_buffer(vertex_data, face_data)).decode(),
                "byteLength": len(vertex_data) * 4 + len(face_data) * 2
            }]
        }
        
        return gltf
    
    def _create_binary_buffer(self, vertex_data: List[float], face_data: List[int]) -> bytes:
        """
        Create a binary buffer for GLTF format
        """
        import struct
        
        buffer = bytearray()
        
        # Add vertex data (each vertex has 3 floats: x, y, z)
        for i in range(0, len(vertex_data), 3):
            buffer.extend(struct.pack('<fff', vertex_data[i], vertex_data[i+1], vertex_data[i+2]))
        
        # Add face data (each face index is a short)
        for idx in face_data:
            buffer.extend(struct.pack('<H', idx))
        
        return buffer
    
    def _create_json_format(self, vertices: List, faces: List) -> Dict:
        """
        Create JSON format dictionary from vertices and faces
        
        Returns:
            JSON format dictionary
        """
        return {
            "vertices": vertices,
            "faces": faces,
            "format_version": "1.0",
            "type": "kd_code_3d_model"
        }
    
    def _estimate_print_time(self, radius: float, height: float, base_thickness: float) -> str:
        """
        Estimate 3D printing time based on model size
        
        Args:
            radius: Radius of the model
            height: Height of the raised elements
            base_thickness: Thickness of the base
        
        Returns:
            Estimated print time as string
        """
        total_height = height + base_thickness
        volume = math.pi * (radius ** 2) * total_height  # Approximate volume in mm³
        
        # Estimate: 1 cm³ takes about 5 minutes to print with 0.2mm layers
        volume_cm3 = volume / 1000  # Convert mm³ to cm³
        estimated_minutes = volume_cm3 * 5
        
        hours = int(estimated_minutes // 60)
        minutes = int(estimated_minutes % 60)
        
        return f"{hours}h {minutes}m"
    
    def _estimate_material_usage(self, radius: float, height: float, base_thickness: float) -> Dict[str, float]:
        """
        Estimate material usage for 3D printing
        
        Args:
            radius: Radius of the model
            height: Height of the raised elements
            base_thickness: Thickness of the base
        
        Returns:
            Dictionary with material estimates
        """
        total_height = height + base_thickness
        volume_mm3 = math.pi * (radius ** 2) * total_height
        volume_cm3 = volume_mm3 / 1000  # Convert to cm³
        
        # Calculate weight based on material density (g/cm³)
        weight_g = volume_cm3 * self.default_material_density
        
        return {
            "volume_cm3": round(volume_cm3, 2),
            "weight_g": round(weight_g, 2),
            "material_type": "PLA"  # Default assumption
        }


# Global 3D generator instance
kd_3d_generator = KDCode3DGenerator()


def generate_3d_kd_code(text: str, **kwargs) -> Dict[str, Any]:
    """
    Generate a 3D model of a KD-Code
    
    Args:
        text: Text to encode in the KD-Code
        **kwargs: Additional parameters for 3D generation
    
    Returns:
        Dictionary containing the 3D model and metadata
    """
    return kd_3d_generator.generate_3d_model(text, **kwargs)


def get_3d_generation_options() -> Dict[str, Any]:
    """
    Get available options for 3D KD-Code generation
    
    Returns:
        Dictionary of available options with defaults
    """
    return {
        'supported_formats': ['stl', 'obj', 'gltf', 'json'],
        'default_height': 2.0,
        'default_base_thickness': 1.0,
        'default_scale_factor': 5,
        'min_height': 0.5,
        'max_height': 10.0,
        'layer_height': 0.2
    }


# Example usage
if __name__ == "__main__":
    # Example of generating a 3D KD-Code
    print("Generating 3D KD-Code model...")
    
    result = generate_3d_kd_code(
        "Hello 3D World!",
        height=3.0,
        base_thickness=2.0,
        output_format='stl'
    )
    
    print(f"3D model generated successfully!")
    print(f"Format: {result['format']}")
    print(f"Dimensions: {result['dimensions']}")
    print(f"Estimated print time: {result['estimated_print_time']}")
    print(f"Material usage: {result['estimated_material_usage']}")
    
    # Save the model to a file
    import os
    output_dir = "3d_models"
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{output_dir}/kd_code_3d_model.stl"
    with open(filename, 'w') as f:
        f.write(result['model'])
    
    print(f"3D model saved to {filename}")