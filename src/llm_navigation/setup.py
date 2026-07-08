import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'llm_navigation'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*'))),
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*'))),
        (os.path.join('share', package_name, 'models'), glob(os.path.join('models', '*'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='subham',
    maintainer_email='subhamchhotaray2006@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            "nav2_goal = llm_navigation.nav2_goal:main",
            "frontier_explorer = llm_navigation.frontier_explorer:main",
            "frontier_selection = llm_navigation.frontier_selection:main",
            "nav2_open_goal = llm_navigation.nav2_open_goal:main",
            "person_detection_yolo = llm_navigation.person_detection_yolo:main",
        ],
    },
)
