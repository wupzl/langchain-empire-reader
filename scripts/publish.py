"""Explicit GitHub admin steps; credentials stay in memory, commits use ordinary Git."""
import argparse
import json
import subprocess
import urllib.error
import urllib.request

OWNER = 'wupzl'
REPO = 'langchain-empire-reader'
BASE = f'/repos/{OWNER}/{REPO}'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['create','pages','status'])
    args = parser.parse_args()
    process = subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,check=True)
    credentials = dict(line.split('=',1) for line in process.stdout.splitlines() if '=' in line)
    token = credentials.get('password')
    if not token:
        raise SystemExit('No GitHub credential available')
    def api(path,method='GET',data=None,optional=False):
        request = urllib.request.Request('https://api.github.com'+path,method=method,data=json.dumps(data).encode('utf-8') if data is not None else None,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json','User-Agent':'langchain-reader-publisher'})
        try:
            with urllib.request.urlopen(request,timeout=30) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as error:
            if optional and error.code == 404:
                return None
            message = json.loads(error.read()).get('message','API request failed')
            raise SystemExit(f'GitHub {method} {path}: {error.code} {message}') from None
    account = api('/user')
    if account['login'] != OWNER:
        raise SystemExit('Authenticated account does not match the requested repository owner')
    if args.action == 'create':
        repo = api(BASE,optional=True)
        if repo is None:
            repo = api('/user/repos','POST',{'name':REPO,'description':'LangChain 帝国：五章小说式 AI 应用工程阅读，Tools、Memory、RAG 与 LangGraph。','private':False,'auto_init':False,'homepage':f'https://{OWNER}.github.io/{REPO}/'})
            print('Created public repository:',repo['html_url'])
        else:
            assert not repo['private'],'Existing repository is private; visibility was not changed'
            print('Public repository already exists:',repo['html_url'])
    elif args.action == 'pages':
        site = api(BASE+'/pages',optional=True)
        if site is None:
            site = api(BASE+'/pages','POST',{'build_type':'legacy','source':{'branch':'main','path':'/docs'}})
        else:
            assert site['source'] == {'branch':'main','path':'/docs'},'Existing Pages source differs; no change made'
        print(json.dumps({'url':site['html_url'],'status':site['status'],'source':site['source']},ensure_ascii=False))
    else:
        site = api(BASE+'/pages',optional=True)
        builds = api(BASE+'/pages/builds/latest',optional=True) if site else None
        runs = api(BASE+'/actions/runs?per_page=5')
        print(json.dumps({'site':{'url':site['html_url'],'status':site['status'],'source':site['source']} if site else None,'latest_build':{'status':builds.get('status'),'commit':builds.get('commit'),'error':builds.get('error')} if builds else None,'runs':[{'name':r['name'],'status':r['status'],'conclusion':r['conclusion'],'url':r['html_url']} for r in runs.get('workflow_runs',[])]},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
