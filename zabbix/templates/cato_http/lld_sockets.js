var root = JSON.parse(value);
var snapshot = root && root.data && root.data.accountSnapshot;
var sites = snapshot && Array.isArray(snapshot.sites) ? snapshot.sites : [];
var pattern = new RegExp('{$CATO.SITE.CONN_TYPE.MATCHES}');
var out = [];
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
    var haRole = 'standalone';
    if (isHA) {
      haRole = (socket.isPrimary === true || String(socket.isPrimary).toLowerCase() === 'true') ? 'primary' : 'secondary';
    }
    out.push({
      '{#SITE.ID}': String(site.id),
      '{#SITE.NAME}': String(info.name || ''),
      '{#SOCKET.ID}': String(socket.id),
      '{#SOCKET.NAME}': String(device.name || ''),
      '{#SERIAL}': String(socket.serial),
      '{#HA.ROLE}': haRole,
      '{#PLATFORM}': String(socket.platform || '')
    });
  }
}
return JSON.stringify(out);
