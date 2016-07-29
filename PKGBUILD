# Скрипт сборки пакета для систем arch linux
# Maintainer: Евгений

pkgname=mopyqtiv
pkgver=0.3.1
pkgrel=1
pkgdesc='Mouse oriented PyQt5 image viewer'
arch=('any')
url="https://github.com/inaugurator/mopyqtiv"
license=('Apache')
depends=('python-pillow' 'python-pyqt5' 'xdg-utils')
provides=('mopyqtiv')
source=("${url}/archive/${pkgver}.tar.gz")
sha256sums=('d3440d4be3dc0c177096a9dd5d35bac04cf5767b397bea23eb44d4101f72d9ac')

package() {

    cd ${pkgname}-${pkgver}
    install -Dpm0755 ${pkgname} ${pkgdir}/usr/bin/mopyqtiv
    install -Dpm0644 config.ini ${pkgdir}/etc/${pkgname}/config.ini
    install -Dpm0644 ${pkgname}.1 ${pkgdir}/usr/share/man/ru/man1/mopyqtiv.1
    install -Dpm0644 ${pkgname}.desktop ${pkgdir}/usr/share/applications/mopyqtiv.desktop
}

# vim: set ts=4 sw=4 tw=0 noet :
