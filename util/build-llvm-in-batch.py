#!/usr/bin/env python3
import argparse
from collections import namedtuple

from hailtop.batch import Batch

LLVM_VERSION = '13.0.0'
SOURCE_URL = f'https://github.com/llvm/llvm-project/releases/download/llvmorg-{LLVM_VERSION}/llvm-project-{LLVM_VERSION}.src.tar.xz'
SOURCE_ROOT_DIRNAME = f'llvm-project-{LLVM_VERSION}.src'

CMAKE_VARIABLES = {
    'CMAKE_BUILD_TYPE': 'Release',
    'CMAKE_INSTALL_PREFIX': '/opt/llvm/',
    'CMAKE_C_COMPILER': 'clang',
    'CMAKE_CXX_COMPILER': 'clang++',
    'LLVM_ENABLE_LLD': 'ON',
    'LLVM_BUILD_EXAMPLES': 'OFF',
    'LLVM_BUILD_TESTS': 'OFF',
    'LLVM_ENABLE_PROJECTS': "'mlir;clang;lld;lldb'",
    'LLVM_ENABLE_ASSERTIONS': 'OFF',
    'LLVM_ENABLE_FFI': 'ON',
    'LLVM_ENABLE_LIBCXX': 'OFF',
    'LLVM_ENABLE_PIC': 'ON',
    'LLVM_ENABLE_RTTI': 'ON',
    'LLVM_ENABLE_SPHINX': 'OFF',
    'LLVM_ENABLE_TERMINFO': 'ON',
    'LLVM_BUILD_LLVM_DYLIB': 'ON',
    'LLVM_LINK_LLVM_DYLIB': 'ON',
    'LLVM_INSTALL_UTILS': 'ON',
    'LLVM_ENABLE_ZLIB': 'ON',
    'MLIR_ENABLE_BINDINGS_PYTHON': 'ON',
}

ImageInfo = namedtuple('ImageInfo', 'image triple base')

DEFAULT_BUILDER = 'gcr.io/hail-vdc/mlir-hail-llvmbuilder:latest'
BUILDERS = (
    ImageInfo(DEFAULT_BUILDER, 'x86_64-unknown-linux-gnu', 'bullseye'),
)
BUILDER_INFO = {info.name: info for info in BUILDERS}


def main():
    parser = argparse.ArgumentParser('batch-build-llvm')
    parser.add_argument('image', help='image to build llvm with',
                        nargs='?',
                        default=DEFAULT_BUILDER,
                        choices=BUILDER_INFO)
    args = parser.parse_args()
    info = BUILDER_INFO[args.image]
    print(args)

    batch = Batch(name=f'build llvm-{LLVM_VERSION} {info.triple} {info.base}')
    job = batch.new_bash_job()
    job.image(args.image)
    job.cpu(16)
    job.memory('standard')
    job.storage('100Gi')
    job.command('mkdir -p /io/src')
    job.command('cd /io/src')
    job.command(f'curl -LsSf {SOURCE_URL} | xz -d | tar xf -')
    job.command(f'mv {SOURCE_ROOT_DIRNAME} llvm-project')
    job.command('mkdir -p llvm-project/build')
    job.command('cd llvm-project/build')
    cmake_command = 'cmake ../llvm -Wno-dev -GNinja ' \
        + f'-DLLVM_DEFAULT_TARGET_TRIPLE={info.triple}' \
        + ' '.join(f'-D{key}={value}' for key, value in CMAKE_VARIABLES.items())
    job.command(cmake_command)
    job.command('ninja')
    # TODO install llvm-lit
    job.command('DESTDIR="$PWD/pkg" ninja install')
    job.command('cd pkg')
    job.command(f'tar cf - opt | zstd -T0 -19 -cv > {job.ofile}')
    batch.write_output(job.ofile, f'llvm_all-backends_{info.triple}_{info.base}_{LLVM_VERSION}.tar.zst')
    batch.run()

if __name__ == '__main__':
    main()
