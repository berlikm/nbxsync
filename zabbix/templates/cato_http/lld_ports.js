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

function portKind(id) {
  var name = String(id || '').toUpperCase();
  if (name.indexOf('LAN') === 0) {
    return 'lan';
  }
  if (name.indexOf('WAN') === 0 || name === 'LTE' || name.indexOf('ALT') === 0) {
    return 'wan';
  }
  return 'other';
}

for (var i = 0; i < sites.length; i++) {
  var site = sites[i];
  var info = site && site.info;
  if (!site || !info || site.id === undefined || site.id === null || !pattern.test(String(info.connType || ''))) {
    continue;
  }
  var isHA = info.isHA === true || String(info.isHA).toLowerCase() === 'true';
  var devices = Array.isArray(site.devices) ? site.devices : [];
  for (var j = 0; j < devices.length; j++) {
    var device = devices[j];
    var socket = device && device.socketInfo;
    if (!socket || socket.id === undefined || socket.id === null || !String(socket.serial || '').trim()) {
      continue;
    }
    var states = Array.isArray(device.interfacesLinkState) ? device.interfacesLinkState : [];
    for (var k = 0; k < states.length; k++) {
      var port = states[k];
      if (!port || port.id === undefined || port.id === null || !String(port.id).trim()) {
        continue;
      }
      if (isUsb(port.id, port.name, port.physicalPort)) {
        continue;
      }
      var kind = portKind(port.id);
      out.push({
        '{#SITE.ID}': String(site.id),
        '{#SITE.NAME}': String(info.name || ''),
        '{#CONN.TYPE}': String(info.connType || ''),
        '{#SOCKET.ID}': String(socket.id),
        '{#SOCKET.NAME}': String(device.name || ''),
        '{#SERIAL}': String(socket.serial),
        '{#HA.ROLE}': normalizeHaRole(device, socket, isHA),
        '{#PORT.ID}': String(port.id),
        '{#PORT.KIND}': kind
      });
    }
  }
}
return JSON.stringify(out);
