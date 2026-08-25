var parsed;
try {
  parsed = JSON.parse(value);
} catch (e) {
  throw 'MSSQL named-instance LLD: invalid WMI JSON';
}
var rows = [];
if (parsed === null) {
  return '[]';
}
if (Object.prototype.toString.call(parsed) === '[object Array]') {
  rows = parsed;
} else if (typeof parsed === 'object') {
  rows = [parsed];
} else {
  return '[]';
}
var PREFIX = 'MSSQL$';
var out = [];
for (var i = 0; i < rows.length; i++) {
  var row = rows[i];
  var name = row && row.Name;
  if (typeof name !== 'string') {
    continue;
  }
  if (name.indexOf(PREFIX) !== 0) {
    continue;
  }
  if (name.indexOf('MSSQLFDLauncher') === 0) {
    continue;
  }
  var instance = name.substring(PREFIX.length);
  if (!instance) {
    continue;
  }
  out.push({
    '{#MSSQL.SERVICE}': name,
    '{#MSSQL.INSTANCE}': instance,
    '{#MSSQL.URI}': 'sqlserver://localhost/' + instance,
    '{#MSSQL.DISPLAY}': row.DisplayName || name
  });
}
return JSON.stringify(out);
