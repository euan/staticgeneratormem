from distutils.core import setup

version = 'euan.1.1'

setup(name='staticgeneratormem',
      version=version,
      description="StaticGeneratorMem for Django",
      author="Andreas Cederstrom",
      author_email="andreas youknowwhathere klydd.se",
      url="http://github.com/andriijas/staticgeneratormem/",
      packages = ['staticgeneratormem'],
      install_requires = ['staticgenerator'],
      )
