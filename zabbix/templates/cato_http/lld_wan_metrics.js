var root = JSON.parse(value);
var metrics = root && root.data && root.data.accountMetrics;
var sites = metrics && Array.isArray(metrics.sites) ? metrics.sites : [];
var pattern = new RegExp('{$CATO.SITE.CONN_TYPE.MATCHES}');
var out = [];
for (var i = 0; i < sites.length; i++) {
  var site = sites[i];
  var info = site && site.info;
  if (!site || !info || site.id === undefined || site.id === null || !pattern.test(String(info.connType || ''))) {
    continue;
  }
  var interfaces = Array.isArray(site.interfaces) ? site.interfaces : [];
  for (var j = 0; j < interfaces.length; j++) {
    var iface = interfaces[j];
    var interfaceInfo = iface && iface.interfaceInfo;
    if (!interfaceInfo || interfaceInfo.id === undefined || interfaceInfo.id === null) {
      continue;
    }
    out.push({
      '{#SITE.ID}': String(site.id),
      '{#LINK.ID}': String(interfaceInfo.id),
      '{#SITE.NAME}': String(site.name || ''),
      '{#CONN.TYPE}': String(info.connType || ''),
      '{#LINK.NAME}': String(iface.name || interfaceInfo.name || ''),
      '{#DEST.TYPE}': String(interfaceInfo.destType || '')
    });
  }
}
return JSON.stringify(out);
