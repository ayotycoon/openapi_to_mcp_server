#prepend

def #method_name(#args)-> #response_body:
    args_debug_str = #debug_args
    mylogger.info(f"[MCP] [#method_name_tool] starting tool - {args_debug_str}")

    try:
        res = requests.request(method="#http_method", url=f"#url", json=#json, headers=#headers)
        mylogger.info(f"[MCP] [#method_name_tool] response status={res.status_code}")
        if res.ok:
            mylogger.info("[MCP] [#method_name_tool] successful OK response")
            r = res.json()
            mylogger.info(f"[MCP] [#method_name_tool] parsed response - {r}", r)
            return r
    except Exception as e:
        mylogger.info(f"[MCP] [#method_name_tool] error response - {e}", e)
    mylogger.info("[MCP] [#method_name_tool] ending tool")

    return None