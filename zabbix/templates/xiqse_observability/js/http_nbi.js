function httpAuthBasic() {
  return typeof HTTPAUTH_BASIC === 'number' ? HTTPAUTH_BASIC : 1;
}

function nbiBase(params) {
  return params.scheme + '://' + params.fqdn + ':' + params.port;
}

function fetchToken(params) {
  var request = new HttpRequest();
  request.addHeader('Content-Type: application/x-www-form-urlencoded');
  request.setHttpAuth(httpAuthBasic(), params.client_id, params.client_secret);
  var url = nbiBase(params) + '/oauth/token/access-token?grant_type=client_credentials';
  var response = request.post(url, '');
  var code = request.getStatus();
  if (code !== 200) {
    return { ok: 0, error: 'oauth HTTP ' + code };
  }
  var body;
  try {
    body = JSON.parse(response);
  } catch (error) {
    return { ok: 0, error: 'oauth invalid JSON' };
  }
  if (!body || !body.access_token) {
    return { ok: 0, error: 'oauth no access_token' };
  }
  return { ok: 1, token: body.access_token };
}

function graphql(params, token, query) {
  var request = new HttpRequest();
  request.addHeader('Accept: application/json');
  request.addHeader('Content-Type: application/json');
  request.addHeader('Authorization: Bearer ' + token);
  var url = nbiBase(params) + '/nbi/graphql';
  var response = request.post(url, JSON.stringify({ query: query }));
  var code = request.getStatus();
  var body;
  try {
    body = JSON.parse(response);
  } catch (error) {
    return { ok: 0, error: 'graphql invalid JSON HTTP ' + code };
  }
  if (code !== 200) {
    return { ok: 0, error: 'graphql HTTP ' + code };
  }
  if (body && Array.isArray(body.errors) && body.errors.length && !body.data) {
    return { ok: 0, error: String(body.errors[0].message || 'graphql error') };
  }
  return {
    ok: 1,
    data: body.data,
    errorCount: body && Array.isArray(body.errors) ? body.errors.length : 0
  };
}

function graphqlTry(params, token, queries) {
  // Prefer a later clean query. On 25.5.12.6 the first engines query asks
  // for connected (not on NacAppliance) and must not win over the fallback.
  var last = { ok: 0, error: 'no graphql query' };
  var partial = null;
  var i;
  for (i = 0; i < queries.length; i++) {
    last = graphql(params, token, queries[i]);
    if (last.ok && !last.errorCount) {
      return last;
    }
    if (last.ok) {
      partial = last;
    }
  }
  return partial || last;
}
