import re
import sys

def patch_file(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # 1. Replace build_libdvdread with Meson version
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
    
    pattern_read = r'build_libdvdread\(\) \{.*?\}\n'
    if re.search(pattern_read, content, flags=re.DOTALL):
        print("Patching build_libdvdread...")
        content = re.sub(pattern_read, new_dvdread + "\n", content, flags=re.DOTALL)
    else:
        print("Error: build_libdvdread pattern not found!")
        sys.exit(1)

    # 2. Replace build_libdvdnav with Meson version
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
    
    pattern_nav = r'build_libdvdnav\(\) \{.*?\}\n'
    if re.search(pattern_nav, content, flags=re.DOTALL):
        print("Patching build_libdvdnav...")
        content = re.sub(pattern_nav, new_dvdnav + "\n", content, flags=re.DOTALL)
    else:
        print("Error: build_libdvdnav pattern not found!")
        sys.exit(1)

    # 3. Disable SVT-AV1
    print("Disabling SVT-AV1...")
    content = content.replace('    build_svt-av1', '    # build_svt-av1')
    content = content.replace('  build_svt-av1', '  # build_svt-av1')
    content = content.replace('--enable-libsvtav1', '')

    # 4. Inject DVD libraries into build tree
    # Remove old injections to be idempotent
    content = re.sub(r'\n\s*build_libdvdread(?!\(\))', '', content)
    content = re.sub(r'\n\s*build_libdvdnav(?!\(\))', '', content)
    
    # Inject after libsrt line (matching full line to avoid trailing comma issues)
    pattern_libsrt = r'(^\s*build_libsrt.*?$)'
    if re.search(pattern_libsrt, content, re.MULTILINE):
        print("Injecting DVD library calls...")
        content = re.sub(pattern_libsrt, r'\1\n  build_libdvdread\n  build_libdvdnav', content, flags=re.MULTILINE)
    else:
        print("Error: build_libsrt anchor not found!")
        sys.exit(1)

    # 5. Enable in FFmpeg configuration
    if '--enable-gnutls' in content:
        print("Enabling DVD libraries in FFmpeg config...")
        if '--enable-libdvdnav' not in content:
            content = content.replace('--enable-gnutls', '--enable-gnutls --enable-libdvdnav --enable-libdvdread')
    else:
        print("Error: --enable-gnutls anchor not found!")
        sys.exit(1)

    with open(filename, 'w') as f:
        f.write(content)
    print("Patching complete.")

if __name__ == "__main__":
    patch_file(sys.argv[1])
