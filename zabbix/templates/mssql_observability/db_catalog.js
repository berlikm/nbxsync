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
var recoveryKey = '{#' + 'RECOVERY_MODEL}';
var out = [];
for (var i = 0; i < data.length; i++) {
  var row = data[i] || {};
  var dbname = String(row.dbname || row.DBName || '');
  if (!dbname) {
    continue;
  }
  var lld = {};
  lld[instanceKey] = instance;
  lld[uriKey] = uri;
  lld[dbKey] = dbname;
  lld[recoveryKey] = String(row.recovery_model == null ? '' : row.recovery_model);
  out.push(lld);
}
return JSON.stringify(out);
