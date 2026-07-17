import os
import shutil
import tempfile
import configparser


def get_version_from_metadata(plugin_dir):
    """Gets the plugin version from the metadata.txt file."""
    metadata_path = os.path.join(plugin_dir, 'metadata.txt')
    config = configparser.ConfigParser()
    config.read(metadata_path)

    if 'general' in config and 'version' in config['general']:
        return config['general']['version']
    raise ValueError("Version not found in metadata.txt")
    
def remove_pycache_dirs(start_dir):
    """Recursively removes all __pycache__ directories."""
    for root, dirs, files in os.walk(start_dir, topdown=False):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                dir_path = os.path.join(root, dir_name)
                shutil.rmtree(dir_path)
                

def get_unique_filename(base_path):
    """Returns a unique file name by adding a suffix if the file already exists."""
    if not os.path.exists(f"{base_path}.zip"):
        return f"{base_path}.zip"
    
    counter = 1
    while os.path.exists(f"{base_path}-{counter}.zip"):
        counter += 1
    
    return f"{base_path}-{counter}.zip"

def create_plugin_archive(plugin_dir):
    """Creates a plugin archive with a unique name."""
    # Get version from metadata.txt
    version = get_version_from_metadata(plugin_dir)

    # Get the plugin's name (folder name)
    plugin_name = os.path.basename(plugin_dir)

    # Base name for the archive
    base_name = f"tau_net_calc_v{version}"
    output_path = os.path.join(os.path.dirname(plugin_dir), base_name)

    # Generate a unique file name
    unique_output_path = get_unique_filename(output_path)

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a folder with the plugin's name in the temporary directory
        plugin_folder_path = os.path.join(temp_dir, plugin_name)
        os.makedirs(plugin_folder_path)

        exclude_items = ['.git', '__pycache__', '.gitignore', '.vscode']

        for item in os.listdir(plugin_dir):
            if item in exclude_items or item.endswith('.bat'):
                continue
            src_path = os.path.join(plugin_dir, item)
            dst_path = os.path.join(plugin_folder_path, item)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, ignore=ignore_unwanted_files)
            else:
                shutil.copy2(src_path, dst_path)

        # Create the archive from the temporary directory
        shutil.make_archive(
            base_name=unique_output_path.rstrip('.zip'),  # Remove the extension for make_archive
            format='zip',
            root_dir=temp_dir,
            base_dir=plugin_name  # This adds the plugin folder to the archive
        )

    print(f"Archive created: {unique_output_path}")

def ignore_unwanted_files(dir, files):
    unwanted = ['.git', '__pycache__', '.gitignore', '.vscode']
    return [f for f in files if f in unwanted or f.endswith('.bat')]

# Define the plugin directory
current_dir = os.path.dirname(os.path.abspath(__file__))
plugin_dir = os.path.abspath(os.path.join(current_dir, '..'))  # Plugin folder

remove_pycache_dirs(plugin_dir)
# Create the archive
create_plugin_archive(plugin_dir)
