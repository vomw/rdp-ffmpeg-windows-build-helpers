import re
import sys

def patch_file(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # 1. Replace build_libdvdread
    new_dvdread = """build_libdvdread() {
  build_libdvdcss
  if [ ! -f "libdvdread-7.0.1/unpacked.successfully" ]; then
    echo "Downloading libdvdread 7.0.1..."
    curl -sL https://download.videolan.org/pub/videolan/libdvdread/7.0.1/libdvdread-7.0.1.tar.xz -o libdvdread-7.0.1.tar.xz
    tar -xf libdvdread-7.0.1.tar.xz
    touch libdvdread-7.0.1/unpacked.successfully
  fi
  cd libdvdread-7.0.1
    generic_meson_ninja_install
  cd ..
}"""
    content = re.sub(r'build_libdvdread\(\) \{.*?cd \.\.\n\}', new_dvdread, content, flags=re.DOTALL)

    # 2. Replace build_libdvdnav
    new_dvdnav = """build_libdvdnav() {
  if [ ! -f "libdvdnav-7.0.0/unpacked.successfully" ]; then
    echo "Downloading libdvdnav 7.0.0..."
    curl -sL https://download.videolan.org/pub/videolan/libdvdnav/7.0.0/libdvdnav-7.0.0.tar.xz -o libdvdnav-7.0.0.tar.xz
    tar -xf libdvdnav-7.0.0.tar.xz
    touch libdvdnav-7.0.0/unpacked.successfully
  fi
  cd libdvdnav-7.0.0
    generic_meson_ninja_install
  cd ..
}"""
    content = re.sub(r'build_libdvdnav\(\) \{.*?cd \.\.\n\}', new_dvdnav, content, flags=re.DOTALL)

    # 3. Disable SVT-AV1 calls
    content = content.replace('    build_svt-av1', '    # build_svt-av1')
    content = content.replace('  build_svt-av1', '  # build_svt-av1')
    
    # 4. Remove SVT-AV1 from FFmpeg config
    content = content.replace('--enable-libsvtav1', '')

    # 5. Inject DVD libraries into build_ffmpeg_dependencies
    # First, remove any existing calls we might have added
    content = re.sub(r'\n\s*build_libdvdread', '', content)
    content = re.sub(r'\n\s*build_libdvdnav', '', content)
    
    # Inject after libsrt
    content = content.replace('build_libsrt # requires gnutls', 'build_libsrt # requires gnutls\n  build_libdvdread\n  build_libdvdnav')

    # 6. Enable in FFmpeg config
    content = content.replace('--enable-gnutls', '--enable-gnutls --enable-libdvdnav --enable-libdvdread')

    with open(filename, 'w') as f:
        f.write(content)

if __name__ == "__main__":
    patch_file(sys.argv[1])
