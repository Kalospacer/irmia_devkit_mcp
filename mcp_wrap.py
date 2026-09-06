import contextlib,runpy
with open('git_mcp_stderr.log','w',encoding='utf8') as f:
 with contextlib.redirect_stderr(f): runpy.run_path('server.py',run_name='__main__')
