"""
Plugin System for KD-Code System
Enables custom encoding schemes and extensions
"""

import os
import sys
import importlib.util
import inspect
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type
from dataclasses import dataclass
import json


@dataclass
class PluginMetadata:
    """Metadata for a KD-Code plugin"""
    name: str
    version: str
    author: str
    description: str
    plugin_type: str  # 'encoder', 'decoder', 'processor', 'ui_extension'
    compatible_versions: List[str]


class KDCodePlugin(ABC):
    """Abstract base class for KD-Code plugins"""
    
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.enabled = True
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata"""
        pass
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the plugin's main function"""
        pass


class EncoderPlugin(KDCodePlugin):
    """Base class for encoder plugins"""
    
    def __init__(self, name: str, version: str):
        super().__init__(name, version)
    
    @abstractmethod
    def encode(self, text: str, **options) -> str:
        """
        Encode text into a KD-Code representation
        
        Args:
            text: Text to encode
            **options: Additional encoding options
        
        Returns:
            Encoded representation (could be base64 image, binary data, etc.)
        """
        pass
    
    def get_encoding_options(self) -> Dict[str, Any]:
        """
        Get available encoding options for this plugin
        
        Returns:
            Dictionary of available options with default values
        """
        return {}


class DecoderPlugin(KDCodePlugin):
    """Base class for decoder plugins"""
    
    def __init__(self, name: str, version: str):
        super().__init__(name, version)
    
    @abstractmethod
    def decode(self, data: Any, **options) -> str:
        """
        Decode KD-Code data back to text
        
        Args:
            data: KD-Code data to decode
            **options: Additional decoding options
        
        Returns:
            Decoded text
        """
        pass
    
    def can_decode(self, data: Any) -> bool:
        """
        Check if this plugin can decode the given data
        
        Args:
            data: Data to check
        
        Returns:
            True if plugin can decode the data, False otherwise
        """
        return True  # Default implementation assumes it can decode any data


class ProcessorPlugin(KDCodePlugin):
    """Base class for processor plugins (modify existing codes)"""
    
    def __init__(self, name: str, version: str):
        super().__init__(name, version)
    
    @abstractmethod
    def process(self, kd_code_data: Any, **options) -> Any:
        """
        Process existing KD-Code data
        
        Args:
            kd_code_data: Existing KD-Code data
            **options: Processing options
        
        Returns:
            Processed KD-Code data
        """
        pass


class UIExtensionPlugin(KDCodePlugin):
    """Base class for UI extension plugins"""
    
    def __init__(self, name: str, version: str):
        super().__init__(name, version)
    
    @abstractmethod
    def get_ui_elements(self) -> Dict[str, Any]:
        """
        Get UI elements provided by this plugin
        
        Returns:
            Dictionary describing UI elements
        """
        pass


class PluginManager:
    """Manages loading, registering, and executing plugins"""
    
    def __init__(self, plugin_dirs: List[str] = None):
        """
        Initialize the plugin manager
        
        Args:
            plugin_dirs: List of directories to search for plugins
        """
        self.plugin_dirs = plugin_dirs or ['./plugins', './kd_core/plugins']
        self.plugins: Dict[str, KDCodePlugin] = {}
        self.encoders: Dict[str, EncoderPlugin] = {}
        self.decoders: Dict[str, DecoderPlugin] = {}
        self.processors: Dict[str, ProcessorPlugin] = {}
        self.ui_extensions: Dict[str, UIExtensionPlugin] = {}
        
        # Create plugin directories if they don't exist
        for plugin_dir in self.plugin_dirs:
            os.makedirs(plugin_dir, exist_ok=True)
    
    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in plugin directories
        
        Returns:
            List of plugin file paths
        """
        plugin_files = []
        
        for plugin_dir in self.plugin_dirs:
            if os.path.exists(plugin_dir):
                for root, dirs, files in os.walk(plugin_dir):
                    for file in files:
                        if file.endswith('.py') and not file.startswith('__'):
                            plugin_files.append(os.path.join(root, file))
        
        return plugin_files
    
    def load_plugin(self, plugin_path: str) -> Optional[KDCodePlugin]:
        """
        Load a plugin from a Python file
        
        Args:
            plugin_path: Path to the plugin file
        
        Returns:
            Loaded plugin instance or None if loading failed
        """
        try:
            # Get module name from file path
            module_name = os.path.splitext(os.path.basename(plugin_path))[0]
            
            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin classes in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if obj != KDCodePlugin and issubclass(obj, KDCodePlugin):
                    # Instantiate the plugin
                    plugin_instance = obj()
                    
                    # Register the plugin based on its type
                    self.register_plugin(plugin_instance)
                    return plugin_instance
        
        except Exception as e:
            print(f"Error loading plugin {plugin_path}: {e}")
            return None
    
    def register_plugin(self, plugin: KDCodePlugin):
        """
        Register a plugin with the manager
        
        Args:
            plugin: Plugin instance to register
        """
        # Add to general plugins list
        self.plugins[plugin.name] = plugin
        
        # Add to specific type lists
        if isinstance(plugin, EncoderPlugin):
            self.encoders[plugin.name] = plugin
        elif isinstance(plugin, DecoderPlugin):
            self.decoders[plugin.name] = plugin
        elif isinstance(plugin, ProcessorPlugin):
            self.processors[plugin.name] = plugin
        elif isinstance(plugin, UIExtensionPlugin):
            self.ui_extensions[plugin.name] = plugin
    
    def load_all_plugins(self):
        """Load all available plugins"""
        plugin_files = self.discover_plugins()
        
        for plugin_file in plugin_files:
            self.load_plugin(plugin_file)
    
    def get_encoder(self, name: str) -> Optional[EncoderPlugin]:
        """
        Get an encoder plugin by name
        
        Args:
            name: Name of the encoder plugin
        
        Returns:
            Encoder plugin or None if not found
        """
        return self.encoders.get(name)
    
    def get_decoder(self, name: str) -> Optional[DecoderPlugin]:
        """
        Get a decoder plugin by name
        
        Args:
            name: Name of the decoder plugin
        
        Returns:
            Decoder plugin or None if not found
        """
        return self.decoders.get(name)
    
    def get_processor(self, name: str) -> Optional[ProcessorPlugin]:
        """
        Get a processor plugin by name
        
        Args:
            name: Name of the processor plugin
        
        Returns:
            Processor plugin or None if not found
        """
        return self.processors.get(name)
    
    def get_ui_extension(self, name: str) -> Optional[UIExtensionPlugin]:
        """
        Get a UI extension plugin by name
        
        Args:
            name: Name of the UI extension plugin
        
        Returns:
            UI extension plugin or None if not found
        """
        return self.ui_extensions.get(name)
    
    def list_encoders(self) -> List[str]:
        """List all available encoder plugins"""
        return list(self.encoders.keys())
    
    def list_decoders(self) -> List[str]:
        """List all available decoder plugins"""
        return list(self.decoders.keys())
    
    def list_processors(self) -> List[str]:
        """List all available processor plugins"""
        return list(self.processors.keys())
    
    def list_ui_extensions(self) -> List[str]:
        """List all available UI extension plugins"""
        return list(self.ui_extensions.keys())
    
    def execute_plugin(self, plugin_name: str, *args, **kwargs) -> Any:
        """
        Execute a plugin by name
        
        Args:
            plugin_name: Name of the plugin to execute
            *args: Arguments to pass to the plugin
            **kwargs: Keyword arguments to pass to the plugin
        
        Returns:
            Result of plugin execution
        """
        plugin = self.plugins.get(plugin_name)
        if plugin and plugin.enabled:
            return plugin.execute(*args, **kwargs)
        else:
            raise ValueError(f"Plugin '{plugin_name}' not found or disabled")


# Global plugin manager instance
plugin_manager = PluginManager()


def initialize_plugin_system(plugin_directories: List[str] = None):
    """
    Initialize the plugin system
    
    Args:
        plugin_directories: Optional list of directories to search for plugins
    """
    global plugin_manager
    if plugin_directories:
        plugin_manager = PluginManager(plugin_directories)
    else:
        plugin_manager = PluginManager()
    
    # Load all available plugins
    plugin_manager.load_all_plugins()


def get_available_encoders() -> List[str]:
    """Get list of available encoder plugins"""
    return plugin_manager.list_encoders()


def get_available_decoders() -> List[str]:
    """Get list of available decoder plugins"""
    return plugin_manager.list_decoders()


def get_available_processors() -> List[str]:
    """Get list of available processor plugins"""
    return plugin_manager.list_processors()


def get_available_ui_extensions() -> List[str]:
    """Get list of available UI extension plugins"""
    return plugin_manager.list_ui_extensions()


def use_encoder(encoder_name: str, text: str, **options) -> str:
    """
    Use a specific encoder plugin to encode text
    
    Args:
        encoder_name: Name of the encoder plugin to use
        text: Text to encode
        **options: Additional encoding options
    
    Returns:
        Encoded KD-Code representation
    """
    encoder = plugin_manager.get_encoder(encoder_name)
    if not encoder:
        raise ValueError(f"Encoder '{encoder_name}' not found")
    
    return encoder.encode(text, **options)


def use_decoder(decoder_name: str, data: Any, **options) -> str:
    """
    Use a specific decoder plugin to decode data
    
    Args:
        decoder_name: Name of the decoder plugin to use
        data: Data to decode
        **options: Additional decoding options
    
    Returns:
        Decoded text
    """
    decoder = plugin_manager.get_decoder(decoder_name)
    if not decoder:
        raise ValueError(f"Decoder '{decoder_name}' not found")
    
    return decoder.decode(data, **options)


# Example plugin implementations
class SampleColorEncoder(EncoderPlugin):
    """Example plugin: Color-enhanced KD-Code encoder"""
    
    def __init__(self):
        super().__init__("color_enhanced_encoder", "1.0.0")
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Color Enhanced Encoder",
            version="1.0.0",
            author="KD-Code Team",
            description="An encoder that creates colorful KD-Codes",
            plugin_type="encoder",
            compatible_versions=["1.0", "1.1"]
        )
    
    def encode(self, text: str, **options) -> str:
        # This would implement color encoding logic
        # For now, we'll just return a placeholder
        import base64
        import json
        
        # Create a mock color-enhanced KD-Code representation
        color_data = {
            "text": text,
            "encoding": "color-enhanced",
            "colors": options.get("colors", ["#FF0000", "#00FF00", "#0000FF"]),
            "pattern": options.get("pattern", "alternating")
        }
        
        # Convert to base64 as a placeholder
        json_str = json.dumps(color_data)
        return base64.b64encode(json_str.encode()).decode()
    
    def get_encoding_options(self) -> Dict[str, Any]:
        return {
            "colors": ["#FF0000", "#00FF00", "#0000FF"],
            "pattern": "alternating",
            "saturation": 1.0
        }


class SampleCompressionDecoder(DecoderPlugin):
    """Example plugin: Compression-aware decoder"""
    
    def __init__(self):
        super().__init__("compression_aware_decoder", "1.0.0")
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Compression Aware Decoder",
            version="1.0.0",
            author="KD-Code Team",
            description="A decoder that handles compressed KD-Code formats",
            plugin_type="decoder",
            compatible_versions=["1.0", "1.1"]
        )
    
    def decode(self, data: Any, **options) -> str:
        # This would implement decompression and decoding logic
        # For now, we'll just return a placeholder
        import base64
        import json
        import gzip
        
        try:
            # Assume data is base64 encoded compressed JSON
            decoded_bytes = base64.b64decode(data)
            decompressed = gzip.decompress(decoded_bytes)
            decompressed_str = decompressed.decode('utf-8')
            data_dict = json.loads(decompressed_str)
            return data_dict.get("text", "")
        except:
            # If decompression fails, treat as regular base64 JSON
            try:
                decoded_str = base64.b64decode(data).decode('utf-8')
                data_dict = json.loads(decoded_str)
                return data_dict.get("text", "")
            except:
                return "Error: Unable to decode data"


# Register example plugins
def register_example_plugins():
    """Register example plugins for demonstration"""
    plugin_manager.register_plugin(SampleColorEncoder())
    plugin_manager.register_plugin(SampleCompressionDecoder())


if __name__ == "__main__":
    # Initialize the plugin system
    initialize_plugin_system()
    
    # Register example plugins
    register_example_plugins()
    
    # List available plugins
    print("Available Encoders:", get_available_encoders())
    print("Available Decoders:", get_available_decoders())
    print("Available Processors:", get_available_processors())
    print("Available UI Extensions:", get_available_ui_extensions())
    
    # Example usage
    if "color_enhanced_encoder" in get_available_encoders():
        encoded = use_encoder("color_enhanced_encoder", "Hello, Plugin World!", colors=["#FF5733", "#33FF57"])
        print(f"Encoded with plugin: {encoded[:50]}...")
        
        # Try to decode with the sample decoder
        if "compression_aware_decoder" in get_available_decoders():
            decoded = use_decoder("compression_aware_decoder", encoded)
            print(f"Decoded: {decoded}")