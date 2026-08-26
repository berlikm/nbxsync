var root = JSON.parse(value);
var snapshot = root && root.data && root.data.accountSnapshot;
var sites = snapshot && Array.isArray(snapshot.sites) ? snapshot.sites : [];
var pattern = new RegExp('{$CATO.SITE.CONN_TYPE.MATCHES}');
var out = [];

function normalizeHaRole(device, socket, isHA) {
  var raw = String((device && device.haRole) || '').trim().toUpperCase();
  if (raw === 'PRIMARY') {
    raw = 'MASTER';
  }
  if (raw === 'SECONDARY') {
    raw = 'BACKUP';
  }
  if (raw === 'STANDALONE') {
    raw = 'NONE';
  }
  if (raw === 'MASTER' || raw === 'BACKUP' || raw === 'NONE') {
    return raw;
  }
  if (!isHA) {
    return 'NONE';
  }
  var primary = socket && (socket.isPrimary === true || String(socket.isPrimary).toLowerCase() === 'true');
  return primary ? 'MASTER' : 'BACKUP';
}

function isUsb() {
  var blob = Array.prototype.join.call(arguments, ' ').toUpperCase();
  return blob.indexOf('USB') !== -1;
}

for (var i = 0; i < sites.length; i++) {
  var site = sites[i];
  var siteInfo = site && site.info;
  if (!site || !siteInfo || site.id === undefined || site.id === null || !pattern.test(String(siteInfo.connType || ''))) {
    continue;
  }
  var isHA = siteInfo.isHA === true || String(siteInfo.isHA).toLowerCase() === 'true';
  var devices = Array.isArray(site.devices) ? site.devices : [];
  for (var j = 0; j < devices.length; j++) {
    var device = devices[j];
    var socket = device && device.socketInfo;
    if (!socket || socket.id === undefined || socket.id === null || !String(socket.serial || '').trim()) {
      continue;
    }
    var interfaces = Array.isArray(device.interfaces) ? device.interfaces : [];
    for (var k = 0; k < interfaces.length; k++) {
      var iface = interfaces[k];
      var info = iface && iface.info;
      if (!info || info.id === undefined || info.id === null) {
        continue;
      }
      if (isUsb(info.id, info.name, iface.name, iface.physicalPort, info.physicalPort)) {
        continue;
      }
      out.push({
        '{#SITE.ID}': String(site.id),
        '{#SITE.NAME}': String(siteInfo.name || ''),
        '{#CONN.TYPE}': String(siteInfo.connType || ''),
        '{#SOCKET.ID}': String(socket.id),
        '{#SOCKET.NAME}': String(device.name || ''),
        '{#LINK.ID}': String(info.id),
        '{#LINK.NAME}': String(info.name || iface.name || ''),
        '{#DEST.TYPE}': String(info.destType || ''),
        '{#SERIAL}': String(socket.serial),
        '{#HA.ROLE}': normalizeHaRole(device, socket, isHA)
      });
    }
  }
}
return JSON.stringify(out);
