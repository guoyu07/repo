%global project dde-qt-dbus-factory
%global repo %{project}

%global _commit 9adc304138497d6fb89bba06a1ed0a25e0f3a599
%global _shortcommit %(c=%{_commit}; echo ${c:0:7})

Name:           deepin-qt-dbus-factory
Version:        0.1.0
Release:        1.git%{_shortcommit}%{?dist}
Summary:        A repository stores auto-generated Qt5 dbus code
License:        GPLv3
URL:            https://github.com/linuxdeepin/dde-qt-dbus-factory
Source0:        %{url}/archive/%{_commit}/%{repo}-%{_shortcommit}.tar.gz

BuildRequires:  python-devel
BuildRequires:  pkgconfig(gl)
BuildRequires:  pkgconfig(Qt5Core)
BuildRequires:  pkgconfig(Qt5DBus)
BuildRequires:  pkgconfig(Qt5Gui)

%description
A repository stores auto-generated Qt5 dbus code.

%package devel
Summary:        Development package for %{name}
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description devel
Header files and libraries for %{name}

%prep
%setup -q -n %{repo}-%{_commit}

%build
%qmake_qt5 LIB_INSTALL_DIR=%{_libdir}
%make_build

%install
%make_install INSTALL_ROOT=%{buildroot}

%files
%{_libdir}/libdframeworkdbus.so.*

%files devel
%{_includedir}/libdframeworkdbus-1.0/
%{_libdir}/pkgconfig/dframeworkdbus.pc
%{_libdir}/libdframeworkdbus.so

%changelog
* Fri May 19 2017 mosquito <sensor.wen@gmail.com> - 0.1.0-1.git9adc304
- Update to 0.1.0
* Sun Feb 26 2017 mosquito <sensor.wen@gmail.com> - 0.0.4-1.gitefa4f7f
- Update to 0.0.4
* Tue Jan 17 2017 mosquito <sensor.wen@gmail.com> - 0.0.3-1.gitffda1af
- Initial build
