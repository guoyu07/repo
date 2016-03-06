# build Atom and Electron packages: https://github.com/tensor5/arch-atom
# RPM spec: https://github.com/helber/fedora-specs
# Error: Module version mismatch. Expected 47, got 43.
# see https://github.com/tensor5/arch-atom/issues/3
%{?nodejs_find_provides_and_requires}
%global debug_package %{nil}
%global _hardened_build 1
%global __provides_exclude_from %{_libdir}/%{name}/node_modules
%global __requires_exclude_from %{_libdir}/%{name}/node_modules
%global __requires_exclude (npm|libnode)

%global project atom
%global repo %{project}
%global npm_ver 2.13.3
%global electron_ver 0.36.10

# commit
%global _commit b8cc0b4fc51965f3ee6e84f3a23ee29230fd5b4b
%global _shortcommit %(c=%{_commit}; echo ${c:0:7})

Name:    atom
Version: 1.5.4
Release: 1.git%{_shortcommit}%{?dist}
Summary: A hack-able text editor for the 21st century

Group:   Applications/Editors
License: MIT
URL:     https://atom.io/
Source0: https://github.com/atom/atom/archive/%{_commit}/%{repo}-%{_shortcommit}.tar.gz

Patch0:  fix-atom-sh.patch
Patch1:  fix-license-path.patch
Patch2:  use-system-apm.patch
Patch3:  use-system-electron.patch

BuildRequires: npm
BuildRequires: node-gyp
BuildRequires: nodejs >= 0.10.0
BuildRequires: nodejs-packaging
BuildRequires: libgnome-keyring-devel
BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires: git-core
BuildRequires: nodejs-atom-package-manager
Requires: nodejs-atom-package-manager
Requires: electron
Requires: http-parser

%description
Atom is a text editor that's modern, approachable, yet hack-able to the core
- a tool you can customize to do anything but also use productively without
ever touching a config file.

Visit https://atom.io to learn more.

%prep
%setup -q -n %repo-%{_commit}
sed -i 's|<lib>|%{_lib}|g' %{P:0} %{P:3}
%patch0 -p1
%patch1 -p1
%patch2 -p1
%patch3 -p1

# apm with system (updated) nodejs cannot 'require' modules inside asar
sed -e "s|, 'generate-asar'||" -i build/Gruntfile.coffee

# They are known to leak data to GitHub, Google Analytics and Bugsnag.com.
sed -i -E -e '/(exception-reporting|metrics)/d' package.json

%build
# Hardened package
export CFLAGS="%{optflags} -fPIC -pie"
export CXXFLAGS="%{optflags} -fPIC -pie"

%if 0%{?fedora} <= 23 || 0%{?rhel}
# Upgrade npm (>=1.4.0)
## Install new npm to INSTALL_PREFIX for build package
npm config set registry="http://registry.npmjs.org/"
npm config set ca ""
npm config set strict-ssl false
npm config set python `which python2`
npm install -g --ca=null --prefix %{buildroot}%{_prefix} npm@%{npm_ver}
## Export PATH to new npm version
export PATH="%{buildroot}%{_bindir}:$PATH"
%endif

# Build package
node-gyp -v; node -v; npm -v; apm -v
## https://github.com/atom/atom/blob/master/script/bootstrap
export ATOM_RESOURCE_PATH=`pwd`
# If unset, ~/.atom/.node-gyp/.atom/.npm is used
## https://github.com/atom/electron/blob/master/docs/tutorial/using-native-node-modules.md
export npm_config_cache="${HOME}/.atom/.npm"
export npm_config_disturl="https://atom.io/download/atom-shell"
export npm_config_target="%{electron_ver}"
#export npm_config_target_arch="x64|ia32"
export npm_config_runtime="electron"
# The npm_config_target is no effect, set ATOM_NODE_VERSION
## https://github.com/atom/apm/blob/master/src/command.coffee
export ATOM_ELECTRON_VERSION="%{electron_ver}"

_packagesToDedupe=(
    'abbrev'
    'amdefine'
    'atom-space-pen-views'
    'cheerio'
    'domelementtype'
    'fs-plus'
    'grim'
    'highlights'
    'humanize-plus'
    'iconv-lite'
    'inherits'
    'loophole'
    'oniguruma'
    'q'
    'request'
    'rimraf'
    'roaster'
    'season'
    'sigmund'
    'semver'
    'through'
    'temp'
)

# Installing packages
apm clean
apm install --verbose
apm dedupe ${_packagesToDedupe[@]}
# Installing build modules
pushd build
npm install --loglevel info
popd
script/grunt --build-dir='atom-build' --channel=stable

%install
install -d %{buildroot}%{_libdir}/%{name}
cp -r atom-build/Atom/resources/app/* %{buildroot}%{_libdir}/%{name}
rm -rf %{buildroot}%{_libdir}/%{name}/node_modules

install -d %{buildroot}%{_datadir}/applications
sed -e \
   's|<%= appName %>|Atom|
    s|<%= description %>|%{summary}|
    s|<%= installDir %>/share/<%= appFileName %>/||
    s|<%= iconPath %>|%{name}|' \
    resources/linux/atom.desktop.in > \
    %{buildroot}%{_datadir}/applications/%{name}.desktop

install -Dm0755 atom-build/Atom/resources/new-app/atom.sh \
    %{buildroot}%{_bindir}/%{name}

# copy over icons in sizes that most desktop environments like
for i in 1024 512 256 128 64 48 32 24 16; do
    install -D -m 0644 atom-build/icons/${i}.png \
      %{buildroot}%{_datadir}/icons/hicolor/${i}x${i}/apps/%{name}.png
done

# find all *.js files and generate node.file-list
pushd atom-build/Atom/resources/app/node_modules
for ext in js json less png svg; do
  find -type f \( -iname *.${ext} -or -perm 755 \) \
    ! -name '.*' \
    ! -name '*.md' \
    ! -name 'CONTRIBUTORS*' \
    ! -name 'CHANGELOG*' \
    ! -name 'LICENSE*' \
    ! -name 'README*' \
    ! -name 'Makefile*' \
    ! -path '*test*' \
    ! -path '*example*' \
    ! -path '*benchmark*' \
    ! -path '*js-beautify/tools*' \
    ! -path '*acorn/bin/*.sh*' \
    -exec install -D '{}' '%{buildroot}%{_libdir}/%{name}/node_modules/{}' \; \
    -exec echo '%%{_libdir}/%{name}/node_modules/{}' >> %{_builddir}/%{repo}-%{_commit}/node.file-list \;
done
popd
sed -i '/ /s|ars/.*.json|ars/*.json|g' node.file-list
sort -u -o node.file-list node.file-list

find %{buildroot} -type f -regextype posix-extended \( \
    -regex '.*js$' -exec sh -c "head -n2 '{}'|grep -q '^#\!/usr/bin/env' && chmod a+x '{}' || chmod 644 '{}'" \; -or \
    -regex '.*(json|less|svg|conf)$' -exec chmod 644 '{}' \; -or \
    -regex '.*node$' -perm 755 -exec strip '{}' \; -or \
    -regex '.*.gitignore' -exec rm -f '{}' \; -or \
    -size 0 -exec rm -f '{}' \; \)

%post
/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null ||:
/usr/bin/update-desktop-database &>/dev/null ||:

%postun
if [ $1 -eq 0 ]; then
    /bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null ||:
    /usr/bin/gtk-update-icon-cache -f -t -q %{_datadir}/icons/hicolor ||:
fi
/usr/bin/update-desktop-database &>/dev/null ||:

%posttrans
/usr/bin/gtk-update-icon-cache -f -t -q %{_datadir}/icons/hicolor ||:

%files -f node.file-list
%defattr(-,root,root,-)
%doc README.md CONTRIBUTING.md docs/
%license LICENSE.md
%{_bindir}/%{name}
%dir %{_libdir}/%{name}
%{_libdir}/%{name}/dot-atom/
%{_libdir}/%{name}/exports/
%{_libdir}/%{name}/less-compile-cache/
%{_libdir}/%{name}/package.json
%{_libdir}/%{name}/resources/
%{_libdir}/%{name}/spec/
%{_libdir}/%{name}/src/
%{_libdir}/%{name}/static/
%{_libdir}/%{name}/vendor/
%{_datadir}/applications/%{name}.desktop
%{_datadir}/icons/hicolor/*/apps/%{name}.png

%changelog
* Sat Mar  5 2016 mosquito <sensor.wen@gmail.com> - 1.5.4-1.gitb8cc0b4
- Release 1.5.4
* Sun Feb 14 2016 mosquito <sensor.wen@gmail.com> - 1.5.3-2.git3e71894
- The package is split into atom, nodejs-atom-package-manager and electron
- Use system apm and electron
- Not generated asar file
- Remove exception-reporting and metrics dependencies from package.json
- Remove unnecessary files
* Sat Feb 13 2016 mosquito <sensor.wen@gmail.com> - 1.5.3-1.git3e71894
- Release 1.5.3
* Sat Feb 13 2016 mosquito <sensor.wen@gmail.com> - 1.5.2-1.git05731e3
- Release 1.5.2
* Fri Feb 12 2016 mosquito <sensor.wen@gmail.com> - 1.5.1-1.git88524b1
- Release 1.5.1
* Fri Feb  5 2016 mosquito <sensor.wen@gmail.com> - 1.4.3-1.git164201e
- Release 1.4.3
* Wed Jan 27 2016 mosquito <sensor.wen@gmail.com> - 1.4.1-2.git2cf2ccb
- Fix https://github.com/FZUG/repo/issues/64
* Tue Jan 26 2016 mosquito <sensor.wen@gmail.com> - 1.4.1-1.git2cf2ccb
- Release 1.4.1
* Sun Jan 17 2016 mosquito <sensor.wen@gmail.com> - 1.4.0-1.gite0dbf94
- Release 1.4.0
* Sun Dec 20 2015 mosquito <sensor.wen@gmail.com> - 1.3.2-1.git473e885
- Release 1.3.2
* Sat Dec 12 2015 mosquito <sensor.wen@gmail.com> - 1.3.1-1.git3937312
- Release 1.3.1
* Thu Nov 26 2015 mosquito <sensor.wen@gmail.com> - 1.2.4-1.git05ef4c0
- Release 1.2.4
* Sat Nov 21 2015 mosquito <sensor.wen@gmail.com> - 1.2.3-1.gitfb5b1ba
- Release 1.2.3
* Sat Nov 14 2015 mosquito <sensor.wen@gmail.com> - 1.2.1-1.git7e902bc
- Release 1.2.1
* Wed Nov 04 2015 mosquito <sensor.wen@gmail.com> - 1.1.0-1.git402f605
- Release 1.1.0
* Thu Sep 17 2015 Helber Maciel Guerra <helbermg@gmail.com> - 1.0.13-1
- Change lib to libnode
* Tue Sep 01 2015 Helber Maciel Guerra <helbermg@gmail.com> - 1.0.10-1
- Release 1.0.10
* Thu Aug 27 2015 Helber Maciel Guerra <helbermg@gmail.com> - 1.0.8-1
- Clean and test spec for epel, centos and fedora
- Release 1.0.8
* Tue Aug 11 2015 Helber Maciel Guerra <helbermg@gmail.com> - 1.0.6-1
- Release 1.0.6
* Thu Aug 06 2015 Helber Maciel Guerra <helbermg@gmail.com> - 1.0.5-1
- Release 1.0.5
* Wed Jul 08 2015 Helber Maciel Guerra <helbermg@gmail.com> - 1.0.1-1
- Release 1.0.1
* Thu Jun 25 2015 Helber Maciel Guerra <helbermg@gmail.com> - 1.0.0-1
- Release 1.0.0
* Wed Jun 10 2015 Helber Maciel Guerra <helbermg@gmail.com> - 0.208.0-1
- Fix atom.desktop
* Tue Jun 09 2015 Helber Maciel Guerra <helbermg@gmail.com> - 0.207.0-1
- Fix desktop icons and some rpmlint.
* Fri Oct 31 2014 Helber Maciel Guerra <helbermg@gmail.com> - 0.141.0-1
- release 0.141.0
* Thu Oct 23 2014 Helber Maciel Guerra <helbermg@gmail.com> - 0.139.0-1
- release 0.139.0
* Wed Oct 15 2014 Helber Maciel Guerra <helbermg@gmail.com> - 0.137.0-2
- release 0.137.0
* Tue Oct 07 2014 Helber Maciel Guerra <helbermg@gmail.com> - 0.136.0-1
- release 0.136.0
* Tue Sep 30 2014 Helber Maciel Guerra <helbermg@gmail.com> - 0.133.0-2
- Build OK
* Fri Aug 22 2014 Helber Maciel Guerra <helbermg@gmail.com> - 0.123.0-2
- Change package name to atom.
* Thu Aug 21 2014 Helber Maciel Guerra <helbermg@gmail.com> - 0.123.0-1
- RPM package is just working.
* Sat Jul 26 2014 Helber Maciel Guerra <helbermg@gmail.com> - 0.119.0-1
- Try without nodejs.
* Tue Jul 01 2014 Helber Maciel Guerra <helbermg@gmail.com> - 0.106.0-1
- Try new version
* Sun May 25 2014 Helber Maciel Guerra <helbermg@gmail.com> - 0.99.0
- Initial package