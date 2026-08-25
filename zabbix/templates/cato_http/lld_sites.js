var root = JSON.parse(value);
var snapshot = root && root.data && root.data.accountSnapshot;
var sites = snapshot && Array.isArray(snapshot.sites) ? snapshot.sites : [];
var pattern = new RegExp('{$CATO.SITE.CONN_TYPE.MATCHES}');
var out = [];
for (var i = 0; i < sites.length; i++) {
  var site = sites[i];
  var info = site && site.info;
  if (!site || !info || site.id === undefined || site.id === null) {
    continue;
  }
  if (!pattern.test(String(info.connType || ''))) {
    continue;
  }
  out.push({
    '{#SITE.ID}': String(site.id),
    '{#SITE.NAME}': String(info.name || ''),
    '{#CONN.TYPE}': String(info.connType || ''),
    '{#IS.HA}': (info.isHA === true || String(info.isHA).toLowerCase() === 'true') ? '1' : '0'
  });
}
return JSON.stringify(out);
