try {
  var parsed = JSON.parse(value);
} catch (error) {
  return '[]';
}
if (parsed == null || parsed === '') {
  return '[]';
}
if (!Array.isArray(parsed)) {
  parsed = [parsed];
}
var out = [];
for (var i = 0; i < parsed.length; i++) {
  var chunk = parsed[i];
  if (chunk == null || chunk === '') {
    continue;
  }
  if (typeof chunk === 'string') {
    try {
      chunk = JSON.parse(chunk);
    } catch (error) {
      continue;
    }
  }
  if (!Array.isArray(chunk)) {
    chunk = [chunk];
  }
  for (var j = 0; j < chunk.length; j++) {
    var row = chunk[j];
    if (row && typeof row === 'object') {
      out.push(row);
    }
  }
}
return JSON.stringify(out);
