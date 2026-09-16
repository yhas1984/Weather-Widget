#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-5.0.4}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="${ROOT}/.package-build"
DIST="${ROOT}/dist"
PKG="${BUILD}/weather-widget_${VERSION}_amd64"

rm -rf "${BUILD}"
mkdir -p "${PKG}/DEBIAN" "${PKG}/opt/weather-widget" "${PKG}/usr/bin" \
    "${PKG}/usr/share/applications" "${PKG}/usr/share/doc/weather-widget" \
    "${PKG}/usr/share/icons/hicolor/512x512/apps" \
    "${PKG}/usr/share/icons/hicolor/scalable/apps"

python3 -m PyInstaller --clean --noconfirm --distpath "${DIST}" --workpath "${BUILD}/pyinstaller" "${ROOT}/WeatherWidget.spec"
install -m 0755 "${DIST}/WeatherWidget" "${PKG}/opt/weather-widget/WeatherWidget"
install -m 0644 "${ROOT}/icon.png" "${PKG}/usr/share/icons/hicolor/512x512/apps/weather-widget.png"
install -m 0644 "${ROOT}/icon.svg" "${PKG}/usr/share/icons/hicolor/scalable/apps/weather-widget.svg"

cat > "${PKG}/usr/bin/weather-widget" <<'EOF'
#!/bin/sh
exec /opt/weather-widget/WeatherWidget "$@"
EOF
chmod 0755 "${PKG}/usr/bin/weather-widget"

cat > "${PKG}/usr/share/applications/weather-widget.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Weather Widget
Comment=Weather Widget V5
Exec=/usr/bin/weather-widget
Icon=weather-widget
StartupWMClass=WeatherWidget
Terminal=false
Categories=Utility;
EOF

cat > "${PKG}/usr/share/doc/weather-widget/SOURCE.txt" <<EOF
Source repository: https://github.com/yhas1984/Weather-Widget
Source commit: $(git -C "${ROOT}" rev-parse HEAD)
Package: weather-widget
Version: ${VERSION}
Architecture: amd64
EOF

cat > "${PKG}/DEBIAN/control" <<EOF
Package: weather-widget
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: yhas1984
Depends: libxcb-xinerama0, hicolor-icon-theme
Description: Weather Widget V5
 Desktop weather widget using Open-Meteo and optional WeatherAPI fallback.
EOF

cat > "${PKG}/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
EOF

cat > "${PKG}/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
EOF
chmod 0755 "${PKG}/DEBIAN/postinst" "${PKG}/DEBIAN/postrm"

OUT="${ROOT}/weather-widget_${VERSION}_amd64.deb"
dpkg-deb --build --root-owner-group "${PKG}" "${OUT}"
dpkg-deb --info "${OUT}"
dpkg-deb --contents "${OUT}" | grep -E 'opt/weather-widget/WeatherWidget|usr/bin/weather-widget|usr/share/applications|usr/share/icons/hicolor|SOURCE.txt'
file "${DIST}/WeatherWidget"
(cd "${ROOT}" && sha256sum "$(basename "${OUT}")" > "$(basename "${OUT}").sha256")
echo "created ${OUT}"
echo "created ${OUT}.sha256"
