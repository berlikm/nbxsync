function attr(attrs, name) {
  var re = new RegExp('\\b' + name + '\\s*=\\s*"([^"]*)"', 'i');
  var m = attrs.match(re);
  if (m) {
    return m[1];
  }
  re = new RegExp('\\b' + name + '\\s*=\\s*\'([^\']*)\'', 'i');
  m = attrs.match(re);
  return m ? m[1] : '';
}

function splitBinding(info) {
  var text = String(info || '');
  var last = text.lastIndexOf(':');
  if (last < 0) {
    return { ip: '*', port: '443', host: '' };
  }
  var host = text.substring(last + 1);
  var rest = text.substring(0, last);
  var last2 = rest.lastIndexOf(':');
  if (last2 < 0) {
    return { ip: '*', port: rest || '443', host: host };
  }
  return {
    ip: rest.substring(0, last2),
    port: rest.substring(last2 + 1),
    host: host,
  };
}

function stripComments(xml) {
  return String(xml).replace(/<!--[\s\S]*?-->/g, '');
}

function stripBrackets(ip) {
  var text = String(ip || '');
  if (text.charAt(0) === '[' && text.charAt(text.length - 1) === ']') {
    return text.substring(1, text.length - 1);
  }
  return text;
}

function parseHttpsBindings(xml) {
  var body = stripComments(xml);
  var out = [];
  var seen = {};
  var siteRe = /<site\b([^>]*)>([\s\S]*?)<\/site>/gi;
  var siteMatch;
  while ((siteMatch = siteRe.exec(body)) !== null) {
    var siteName = attr(siteMatch[1], 'name') || 'site';
    var inner = siteMatch[2];
    var bindRe = /<binding\b([^>]*?)\/?>/gi;
    var bindMatch;
    while ((bindMatch = bindRe.exec(inner)) !== null) {
      var attrs = bindMatch[1];
      var proto = attr(attrs, 'protocol');
      if (String(proto).toLowerCase() !== 'https') {
        continue;
      }
      var parts = splitBinding(attr(attrs, 'bindingInformation'));
      var ip = parts.ip || '*';
      var port = parts.port || '443';
      var host = parts.host || '';
      var connect = ip === '*' || ip === '' ? '127.0.0.1' : stripBrackets(ip);
      var sni = host !== '' ? host : connect;
      var bindId = siteName + '/' + ip + '/' + port + '/' + (host !== '' ? host : '_');
      if (seen[bindId]) {
        continue;
      }
      seen[bindId] = true;
      out.push({
        '{#IIS.SITE}': siteName,
        '{#IIS.IP}': ip,
        '{#IIS.PORT}': port,
        '{#IIS.HOST}': host,
        '{#IIS.SNI}': sni,
        '{#IIS.CONNECT}': connect,
        '{#IIS.HAS_HOST}': host !== '' ? '1' : '0',
        '{#IIS.BIND}': bindId,
      });
    }
  }
  return out;
}

return JSON.stringify(parseHttpsBindings(value));
