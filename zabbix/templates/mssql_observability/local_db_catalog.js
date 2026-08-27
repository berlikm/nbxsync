try {
  var data = JSON.parse(value);
} catch (error) {
  return '[]';
}
if (data == null || data === '') {
  return '[]';
}
if (!Array.isArray(data)) {
  data = [data];
}
var instance = '{#MSSQL.INSTANCE}';
var uri = '{#MSSQL.URI}';
var instanceKey = '{#' + 'MSSQL.INSTANCE}';
var uriKey = '{#' + 'MSSQL.URI}';
var dbKey = '{#' + 'DBNAME}';
var groupKey = '{#' + 'GROUP_NAME}';
var out = [];
for (var i = 0; i < data.length; i++) {
  var row = data[i] || {};
  var dbname = String(row.dbname || row.DBName || '');
  var group = String(row.group_name || row.groupName || '');
  if (!dbname || !group) {
    continue;
  }
  var lld = {};
  lld[instanceKey] = instance;
  lld[uriKey] = uri;
  lld[dbKey] = dbname;
  lld[groupKey] = group;
  out.push(lld);
}
return JSON.stringify(out);
