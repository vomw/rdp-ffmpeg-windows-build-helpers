import re
import sys

def patch_file(filename):
    with open(filename, 'r') as f:
        content = f.read()

    # 1. Replace build_libdvdread with Meson version
    # Note: Removed -Dcss=enabled because it causes "Unknown options" error in 7.0.1
    new_dvdread = """build_libdvdread() {
  build_libdvdcss
  if [ ! -f \"libdvdread-7.0.1/unpacked.successfully\" ]; then
    echo \"Downloading libdvdread 7.0.1...\"
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
  if [ ! -f \"libdvdnav-7.0.0/unpacked.successfully\" ]; then
    echo \"Downloading libdvdnav 7.0.0...\"
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

    # 6. Fix Meson cross-file pkgconfig and deprecations
    print("Fixing build_meson_cross pkg-config and properties...")
    content = content.replace("pkgconfig = '${cross_prefix}pkg-config'", "pkgconfig = 'pkg-config'")
    content = content.replace("[properties]", "[built-in options]")

    # 7. Fix mfx_dispatch Automake error if it exists
    # Makefile.am:54: error: 'libintel_gfx_api-x64.a' is not a standard libtool library name
    if 'build_intel_qsv_mfx() {' in content:
        print("Patching mfx_dispatch build to fix Automake error...")
        # Use a more robust way to insert the sed commands
        mfx_patch = 'cd mfx_dispatch_git\n    sed -i \"s/libintel_gfx_api-x64.a/libintel_gfx_api_x64.la/g\" Makefile.am || true\n    sed -i \"s/libintel_gfx_api-x86.a/libintel_gfx_api_x86.la/g\" Makefile.am || true'
        content = content.replace('cd mfx_dispatch_git', mfx_patch)

    # 8. Upgrade libdvdcss to 1.4.3 (latest Autotools version)
    print("Upgrading libdvdcss to 1.4.3...")
    content = content.replace('https://download.videolan.org/pub/videolan/libdvdcss/1.2.13/libdvdcss-1.2.13.tar.bz2', 
                              'https://download.videolan.org/pub/videolan/libdvdcss/1.4.3/libdvdcss-1.4.3.tar.bz2')

    # 9. Fix possible issue with too long touchfile names in do_meson
    print("Fixing do_meson touchfile name length...")
    content = content.replace('local touch_name=$(get_small_touchfile_name already_built_meson "$configure_options $configure_name $LDFLAGS $CFLAGS")',
                              'local touch_name=$(get_small_touchfile_name already_built_meson "$configure_name $LDFLAGS $CFLAGS")')

    # 10. Add SPIRV-Headers build and call
    if 'build_spirv_headers' not in content:
        print("Adding build_spirv_headers...")
        spirv_func = """build_spirv_headers() {
  do_git_checkout https://github.com/KhronosGroup/SPIRV-Headers.git
  cd SPIRV-Headers_git
    do_cmake_and_install \"-DCMAKE_BUILD_TYPE=Release\"
  cd ..
}

"""
        # Insert before build_vulkan definition
        content = content.replace('build_vulkan() {', spirv_func + 'build_vulkan() {')
        
        # Insert call before build_vulkan call
        content = content.replace('    build_vulkan', '    build_spirv_headers\n    build_vulkan')

    # 11. Fix missing timeapi.h in some MinGW-w64 versions
    if 'Fixing missing timeapi.h' not in content:
        print("Adding timeapi.h fix...")
        timeapi_fix = """  build_meson_cross
  # Fix missing timeapi.h in some MinGW-w64 versions
  if [ ! -f "${mingw_w64_x86_64_prefix}/include/timeapi.h" ]; then
    echo "Creating missing timeapi.h..."
    mkdir -p "${mingw_w64_x86_64_prefix}/include"
    cat > "${mingw_w64_x86_64_prefix}/include/timeapi.h" << EOF
#ifndef _TIMEAPI_H_
#define _TIMEAPI_H_
#include <mmsystem.h>
#endif
EOF
  fi"""
        content = content.replace('  build_meson_cross', timeapi_fix)

    with open(filename, 'w') as f:
        f.write(content)
    print("Patching complete.")

if __name__ == "__main__":
    patch_file(sys.argv[1])
