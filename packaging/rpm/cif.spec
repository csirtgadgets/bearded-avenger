%define name bearded-avenger
%define _version $VERSION

Name:      %{name}
Version:   %{_version}
Release:   1%{?dist}
Url:       https://github.com/csirtgadgets/bearded-avenger
Summary:   The smartest way to consume threat intelligence.
License:   GPLv3
Group:     Development/Libraries
Source:    https://github.com/csirtgadgets/bearded-avenger/archive/%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot

BuildArch: noarch

%description

The smartest way to consume threat intelligence.

%prep
%setup -q

%build
echo "nothing to build"

%install
cp -a cif* /usr/bin/

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)

%changelog

* 2015-09-28  <wes@csirtgadgets.org> - 3.0.0-1
- Release of 3.0.0a1