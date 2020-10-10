import subprocess, re, os, tempfile

class GitError(Exception):
    pass
class SHAError(GitError):
    pass
class ExecutionError(GitError):
    def __init__(self, errcode):
        self.error_code = errcode

def _check(process):
    if process.returncode != 0:
        raise ExecutionError(process.returncode)

_sha_re = re.compile('^[0-9a-fA-F]*$')

def rev_parse(rev='HEAD', tree=None):
    process = subprocess.Popen(['git', 'rev-parse', rev],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               close_fds=True, universal_newlines=True, cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)

    sha = stdout.strip()
    if not _sha_re.match(sha):
        raise SHAError()
    return sha

def clean(tree=None):
    cmd = ['git', 'clean', '-f', '-x', '-d', '-q']

    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               close_fds=True, universal_newlines=True, cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)

def fetch(tree=None):
    cmd = ['git', 'fetch']

    process = subprocess.Popen(cmd, cwd=tree)
    process.wait()
    _check(process)

def status(tree=None):
    '''
    Return a list (that may be empty) of current changes. Each entry is a
    tuple, just like returned from git status, with the difference that
    the filename(s) are no longer space-separated but rather the tuple is
    of the form
    ('XY', 'filename')
    or
    ('XY', 'filename_to', 'filename_from')   [if X is 'R' for rename]
    '''
    cmd = ['git', 'status', '--porcelain', '-z']

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, close_fds=True,
                               universal_newlines=True, cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)

    l = stdout.split('\0')
    result = []
    cur = []
    for i in l:
        if not i:
            continue
        if not cur:
            cur.append(i[:2])
            assert i[2] == ' '
            cur.append(i[3:])
            if i[0] == 'R':
                continue
        else:
            cur.append(i)
        result.append(tuple(cur))
        cur = []

    return result

def describe(rev='HEAD', tree=None, extra_args=[]):
    cmd = ['git', 'describe', '--always']

    cmd.extend(extra_args)
    if rev is not None:
        cmd.append(rev)

    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               close_fds=True, universal_newlines=True, cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)

    return stdout.strip()

def verify(git_tree):
    tag = describe(rev=None, tree=git_tree, extra_args=['--dirty'])
    cmd = ['git', 'tag', '-v', tag]

    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               close_fds=True, universal_newlines=True, cwd=git_tree)
    stdout = process.communicate()[0]
    process.wait()

    return dict(r=process.returncode, output=stdout)

def paranoia(tree):
    clean(tree)
    poo = status(tree)
    if (poo):
        return dict(r=-1, output=poo)
    return verify(tree)

def init(tree=None):
    process = subprocess.Popen(['git', 'init'],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               close_fds=True, universal_newlines=True, cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)

def add(path, tree=None):
    process = subprocess.Popen(['git', 'add', '--ignore-removal', path],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               close_fds=True, universal_newlines=True, cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)

def commit_all(message, tree=None):
    add('.', tree=tree)
    process = subprocess.Popen(['git', 'commit', '--allow-empty', '-a', '-m', message],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               close_fds=True, universal_newlines=True, cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)

def ls_tree(rev, files, tree=None):
    process = subprocess.Popen(['git', 'ls-tree', '-z', '-r', rev, '--', ] + list(files),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               close_fds=True, universal_newlines=True, cwd=tree)
    stdout = process.communicate()[0]
    files = stdout.split('\0')
    ret = []
    for f in files:
        if not f:
            continue
        meta, f = f.split('\t', 1)
        meta = meta.split()
        meta.append(f)
        ret.append(meta)
    process.wait()
    _check(process)
    return ret

def get_blob(blob, outf, tree=None):
    try:
        import git, gitdb
        r = git.Repo(path=tree)
        b = r.rev_parse(blob + '^{blob}')
        b.stream_data(outf)
    except ImportError:
        process = subprocess.Popen(['git', 'show', blob],
                                   stdout=outf, close_fds=True, cwd=tree)
        process.wait()
        _check(process)

def clone(gittree, outputdir, options=[]):
    process = subprocess.Popen(['git', 'clone'] + options + [gittree, outputdir])
    process.wait()
    _check(process)

def set_origin(giturl, gitdir):
    process = subprocess.Popen(['git', 'remote', 'rm', 'origin'],
                               close_fds=True, universal_newlines=True, cwd=gitdir)
    process.wait()

    process = subprocess.Popen(['git', 'remote', 'add', 'origin', giturl],
                               close_fds=True, universal_newlines=True, cwd=gitdir)
    process.wait()
    _check(process)

def remote_update(gitdir):
    process = subprocess.Popen(['git', 'remote', 'update'],
                               close_fds=True, universal_newlines=True, cwd=gitdir)
    process.wait()
    _check(process)

def shortlog(from_commit, to_commit, tree=None, files=None):
    if files:
        fargs = ['--'] + files
    else:
        fargs = []
    process = subprocess.Popen(['git', 'shortlog', from_commit + '..' + to_commit] + fargs,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               close_fds=True, universal_newlines=True,
                               cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)
    return stdout

def commit_env_vars(commitid, tree=None):
    process = subprocess.Popen(['git', 'show', '--name-only',
                                '--format=format:GIT_AUTHOR_NAME=%an%nGIT_AUTHOR_EMAIL=%ae%nGIT_AUTHOR_DATE=%aD%x00',
                                commitid],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                close_fds=True, universal_newlines=True,
                                cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)
    data = stdout.split('\x00')[0]
    vals = data.split('\n')
    d = {}
    for k, v in map(lambda x: x.split('=', 1), vals):
        d[k] = v
    return d

def commit_message(commitid, tree=None):
    process = subprocess.Popen(['git', 'show', '--name-only',
                                '--format=format:%s%n%n%b%x00', commitid],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                close_fds=True, universal_newlines=True,
                                cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)
    return stdout.split('\x00')[0]

def remove_config(cfg, tree=None):
    process = subprocess.Popen(['git', 'config', '--unset-all', cfg],
                               close_fds=True, universal_newlines=True, cwd=tree)
    process.wait()
    _check(process)

def ls_remote(branch, tree=None, remote='origin'):
    process = subprocess.Popen(['git', 'ls-remote', '--exit-code', remote, 'refs/heads/' + branch],
                               stdout=subprocess.PIPE,
                               close_fds=True, universal_newlines=True, cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)
    sha = stdout.split()[0]
    if not _sha_re.match(sha):
        raise SHAError()
    return sha

def add(fn, tree=None):
    process = subprocess.Popen(['git', 'add', '--ignore-removal', fn], cwd=tree,
                               close_fds=True, universal_newlines=True)
    process.wait()
    _check(process)

def commit(msg, tree=None, env = {}, opts=[]):
    stdin = tempfile.NamedTemporaryFile(mode='wr')
    stdin.write(msg)
    stdin.seek(0)
    process = subprocess.Popen(['git', 'commit', '--file=-'] + opts,
                               stdin=stdin.file, universal_newlines=True, env=env,
                               cwd=tree)
    process.wait()
    _check(process)

def push(opts=[], tree=None):
    process = subprocess.Popen(['git', 'push'] + opts,
                               close_fds=True, universal_newlines=True, cwd=tree)
    process.wait()
    _check(process)

def log_commits(from_commit, to_commit, tree=None):
    process = subprocess.Popen(['git', 'log', '--first-parent', '--format=format:%H',
                                from_commit + '..' + to_commit],
                               stdout=subprocess.PIPE,
                               close_fds=True, universal_newlines=True,
                               cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)
    vals = stdout.split()
    vals.reverse()
    return vals

def commit_env_vars(commitid, tree=None):
    process = subprocess.Popen(['git', 'show', '--name-only',
                                '--format=format:GIT_AUTHOR_NAME=%an%nGIT_AUTHOR_EMAIL=%ae%nGIT_AUTHOR_DATE=%aD%x00',
                                commitid],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                close_fds=True, universal_newlines=True,
                                cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)
    data = stdout.split('\x00')[0]
    vals = data.split('\n')
    d = {}
    for k, v in map(lambda x: x.split('=', 1), vals):
        d[k] = v
    return d

def rm(opts=[], tree=None):
    process = subprocess.Popen(['git', 'rm'] + opts,
                               close_fds=True, universal_newlines=True, cwd=tree)
    process.wait()
    _check(process)

def reset(opts=[], tree=None):
    process = subprocess.Popen(['git', 'reset'] + opts,
                               close_fds=True, universal_newlines=True, cwd=tree)
    process.wait()
    _check(process)

def diff(tree=None, extra_args=None):
    cmd = ['git', 'diff', '--color=always'] + extra_args

    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               close_fds=True, universal_newlines=True, cwd=tree)
    stdout = process.communicate()[0]
    process.wait()
    _check(process)

    return stdout
