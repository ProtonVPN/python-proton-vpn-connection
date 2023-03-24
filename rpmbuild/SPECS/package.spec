%define unmangled_name proton-vpn-connection
%define version 0.6.0
%define release 1

Prefix: %{_prefix}

Name: python3-%{unmangled_name}
Version: %{version}
Release: %{release}%{?dist}
Summary: %{unmangled_name} library

Group: ProtonVPN
License: GPLv3
Vendor: Proton Technologies AG <opensource@proton.me>
URL: https://github.com/ProtonVPN/%{unmangled_name}
Source0: %{unmangled_name}-%{version}.tar.gz
BuildArch: noarch
BuildRoot: %{_tmppath}/%{unmangled_name}-%{version}-%{release}-buildroot

BuildRequires: python3-setuptools
BuildRequires: python3-jinja2
BuildRequires: python3-proton-core
BuildRequires: python3-proton-vpn-logger
BuildRequires: python3-proton-vpn-killswitch

Requires: python3-jinja2
Requires: python3-proton-core
Requires: python3-proton-vpn-logger
Requires: python3-proton-vpn-killswitch

%{?python_disable_dependency_generator}

%description
Package %{unmangled_name} library.


%prep
%setup -n %{unmangled_name}-%{version} -n %{unmangled_name}-%{version}

%build
python3 setup.py build

%install
python3 setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES


%files -f INSTALLED_FILES
%{python3_sitelib}/proton/
%{python3_sitelib}/proton_vpn_connection-%{version}*.egg-info/
%defattr(-,root,root)

%changelog
* Fri Mar 24 2023 Alexandru Cheltuitor <alexandru.cheltuitor@proton.ch> 0.6.0
- Add IPv6 leak protection

* Tue Feb 14 2023 Alexandru Cheltuitor <alexandru.cheltuitor@proton.ch> 0.5.0
- Use standardized path for connection persistence

* Fri Dec 30 2022 Josep Llaneras <josep.llaneras@proton.ch> 0.4.2
- Release connection resources on errors

* Tue Dec 20 2022 Alexandru Cheltuitor <alexandru.cheltuitor@proton.ch> 0.4.1
- Fix log message
- Refactor state machine so that it runs actions just after each state change

* Wed Dec 14 2022 Josep Llaneras <josep.llaneras@proton.ch> 0.4.0
- Add device disconnected event

* Mon Dec 05 2022 Josep Llaneras <josep.llaneras@proton.ch> 0.3.0
- Persist VPN connection server to disk

* Mon Nov 15 2022 Alexandru Cheltuitor <alexandru.cheltuitor@proton.ch> 0.2.1
- Add vpn logger package

* Fri Nov 11 2022 Alexandru Cheltuitor <alexandru.cheltuitor@proton.ch> 0.2.0
- Ensure that the state machine stops at error

* Fri Nov 4 2022 Josep Llaneras <josep.llaneras@proton.ch> 0.1.0
- Pass current connection to connection status subscribers

* Tue Sep 13 2022 Josep Llaneras <josep.llaneras@proton.ch> 0.0.2
- Fix issue creating connection persistence directory

* Wed Jun 1 2022 Proton Technologies AG <opensource@proton.me> 0.0.1
- First RPM release
