Name:           mopyqtiv
Version:        0.1
Release:        1%{?dist}
Summary:        Mouse oriented PyQt5 image viewer

License:        ASL 2.0
URL:            https://github.com/inaugurator/mopyqtiv
Source0:        %{url}/archive/%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  coreutils
BuildRequires:  desktop-file-utils
Requires:       python3-pillow
Requires:       python3-PyQt5

%description
%{summary}.

%prep
%autosetup

%build
# Nothing to build

%install
install -Dpm0755 %{name} %{buildroot}%{_bindir}/%{name}
install -Dpm0644 %{name}.1 %{buildroot}%{_mandir}/man1/%{name}.1
install -Dpm0644 %{name}.desktop %{buildroot}%{_datadir}/applications/%{name}.desktop

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{name}.desktop

%files
%license LICENSE
%doc README.md
%doc %{_mandir}/man1/%{name}.1*
%{_bindir}/%{name}
%{_datadir}/applications/%{name}.desktop

%changelog
* Thu Jul 14 2016 Igor Gnatenko <i.gnatenko.brain@gmail.com> - 0.1-1
- Initial package
