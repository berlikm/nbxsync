var root = JSON.parse(value);
var metrics = root && root.data && root.data.accountMetrics;
var sites = metrics && Array.isArray(metrics.sites) ? metrics.sites : [];
var pattern = new RegExp('{$CATO.SITE.CONN_TYPE.MATCHES}');
var allowed = {};

function isUsb() {
  var blob = Array.prototype.join.call(arguments, ' ').toUpperCase();
  return blob.indexOf('USB') !== -1;
}

function isLan(transport, iface) {
  var kind = String(transport || '').trim().toUpperCase();
  var name = String(iface || '').trim().toUpperCase();
  if (isUsb(kind, name)) {
    return false;
  }
  if (kind === 'LAN') {
    return true;
  }
  if (kind === 'WAN' || kind === 'LTE' || kind === 'TUNNEL' || kind === 'BYPASS' || kind.indexOf('OFF') === 0) {
    return false;
  }
  return name.indexOf('LAN') === 0;
}

for (var i = 0; i < sites.length; i++) {
  var site = sites[i];
  var info = site && site.info;
  if (!site || site.id === undefined || site.id === null || !pattern.test(String((info && info.connType) || ''))) {
    continue;
  }
  allowed[String(site.id)] = {
    name: String(site.name || (info && info.name) || ''),
    connType: String((info && info.connType) || '')
  };
}

var portMetrics = root && root.data && root.data.socketPortMetrics;
var records = portMetrics && Array.isArray(portMetrics.records) ? portMetrics.records : [];
var out = [];
var seen = {};
for (var r = 0; r < records.length; r++) {
  var map = records[r] && records[r].fieldsMap && typeof records[r].fieldsMap === 'object'
    ? records[r].fieldsMap
    : {};
  var siteId = map.site_id !== undefined && map.site_id !== null ? String(map.site_id) : '';
  var iface = map.socket_interface !== undefined && map.socket_interface !== null
    ? String(map.socket_interface)
    : '';
  var transport = map.transport_type !== undefined && map.transport_type !== null
    ? String(map.transport_type)
    : '';
  if (!siteId || !iface || !allowed[siteId] || !isLan(transport, iface)) {
    continue;
  }
  var key = siteId + '\0' + iface;
  if (seen[key]) {
    continue;
  }
  seen[key] = true;
  out.push({
    '{#SITE.ID}': siteId,
    '{#SITE.NAME}': String(map.site_name || allowed[siteId].name || ''),
    '{#CONN.TYPE}': allowed[siteId].connType,
    '{#PORT.ID}': iface,
    '{#PORT.KIND}': 'lan',
    '{#TRANSPORT}': transport || 'LAN'
  });
}
return JSON.stringify(out);
