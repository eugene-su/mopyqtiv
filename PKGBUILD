# Скрипт сборки пакета для систем arch linux
# Автор: Евгений

pkgname=mopyqtiv
pkgver=0.1
pkgrel=1
pkgdesc='Mouse oriented PyQt5 image viewer'
arch=('i686' 'x86_64')
url="https://github.com/inaugurator/mopyqtiv"
license=('Apache 2.0')
depends=('python' 'python-pillow' 'python-pyqt5')
provides=('mopyqtiv')
source=("git+https://github.com/inaugurator/mopyqtiv.git")
sha256sums=('SKIP')

package() {

    cd ${pkgname}

    mkdir -p "$pkgdir/usr/bin"
    install -m755 mopyqtiv "$pkgdir/usr/bin"

    gzip -9 mopyqtiv.1
    mkdir -p "$pkgdir/usr/share/man/ru/man1/"
    install -m755 mopyqtiv.1.gz "$pkgdir/usr/share/man/ru/man1/"
}

# vim: set ts=4 sw=4 tw=0 noet :
