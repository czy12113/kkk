from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'lidar_to_serial_py'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'examples', 'cpp'), glob('examples/cpp/*')),
        (os.path.join('share', package_name, 'tools'), glob('tools/*.py')),
    ],
    install_requires=['setuptools', 'pyserial'],
    zip_safe=True,
    maintainer='sunrise',
    maintainer_email='user@todo.todo',
    description='Send lidar data to flight controller via serial port',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'lidar_serial_bridge = lidar_to_serial_py.nodes.lidar_serial_bridge:main',
            'lidar_fc_bridge = lidar_to_serial_py.nodes.lidar_fc_bridge:main',
        ],
    },
)
