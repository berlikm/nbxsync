var root = JSON.parse(value);
var snapshot = root && root.data && root.data.accountSnapshot;
var sites = snapshot && Array.isArray(snapshot.sites) ? snapshot.sites : [];
var pattern = new RegExp('{$CATO.SITE.CONN_TYPE.MATCHES}');
var out = [];
for (var i = 0; i < sites.length; i++) {
  var site = sites[i];
  var siteInfo = site && site.info;
  if (!site || !siteInfo || site.id === undefined || site.id === null || !pattern.test(String(siteInfo.connType || ''))) {
    continue;
  }
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
      out.push({
        '{#SITE.ID}': String(site.id),
        '{#SITE.NAME}': String(siteInfo.name || ''),
        '{#SOCKET.ID}': String(socket.id),
        '{#LINK.ID}': String(info.id),
        '{#LINK.NAME}': String(info.name || iface.name || ''),
        '{#SERIAL}': String(socket.serial)
      });
    }
  }
}
return JSON.stringify(out);
