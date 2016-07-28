# Скрипт сборки пакета для систем arch linux
# Maintainer: Евгений

pkgname=mopyqtiv
pkgver=0.3
pkgrel=1
pkgdesc='Mouse oriented PyQt5 image viewer'
arch=('any')
url="https://github.com/inaugurator/mopyqtiv"
license=('Apache')
depends=('python-pillow' 'python-pyqt5' 'xdg-utils')
provides=('mopyqtiv')
source=('https://github.com/inaugurator/mopyqtiv/archive/0.3.tar.gz')
sha256sums=('b71ec2b0cdbfd550eb0b159f5d9102f9f5f58b7cc6b895ad01551eda84f31249')

package() {

    cd ${pkgname}-${pkgver}
    install -Dpm0755 ${pkgname} ${pkgdir}/usr/bin/mopyqtiv
    install -Dpm0644 config.ini ${pkgdir}/etc/${pkgname}/config.ini
    install -Dpm0644 ${pkgname}.1 ${pkgdir}/usr/share/man/ru/man1/mopyqtiv.1
    install -Dpm0644 ${pkgname}.desktop ${pkgdir}/usr/share/applications/mopyqtiv.desktop
}

# vim: set ts=4 sw=4 tw=0 noet :
