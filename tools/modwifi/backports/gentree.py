#!/usr/bin/env python
#
# Generate the output tree into a specified directory.
#

import argparse, sys, os, errno, shutil, re, subprocess
import tarfile, gzip

# find self
source_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(source_dir)
# and import libraries we have
from lib import kconfig, patch, make
from lib import bpgit as git
from lib import bpgpg as gpg
from lib import bpkup as kup
from lib.tempdir import tempdir
from lib import bpreqs as reqs
from lib import bpversion as gen_version

class Bp_Identity(object):
    """
    folks considering multiple integrations may want to
    consider stuffing versioning info here as well but
    that will need thought/design on sharing compat and
    module namespaces.

    Use the *_resafe when combining on regexps, although we currently
    don't support regexps there perhaps later we will and this will
    just make things safer for the output regardless. Once and if those
    are added, how we actually use the others for regular printing will
    need to be considered.
    """
    def __init__(self, integrate=False, kconfig_prefix='CPTCFG_',
                 project_prefix='', project_dir='',
                 target_dir='', target_dir_name='',
                 kconfig_source_var=None):
        self.integrate = integrate
        self.kconfig_prefix = kconfig_prefix
        self.kconfig_prefix_resafe = re.escape(kconfig_prefix)
        self.project_prefix = project_prefix
        self.project_prefix_resafe = re.escape(project_prefix)
        self.full_prefix = kconfig_prefix + project_prefix
        self.full_prefix_resafe = re.escape(self.full_prefix)
        self.project_dir = project_dir
        self.target_dir = target_dir
        self.target_dir_name = target_dir_name
        self.kconfig_source_var = kconfig_source_var
        if self.kconfig_source_var:
            self.kconfig_source_var_resafe = re.escape(self.kconfig_source_var)
        else:
            self.kconfig_source_var_resafe = None

def read_copy_list(copyfile):
    """
    Read a copy-list file and return a list of (source, target)
    tuples. The source and target are usually the same, but in
    the copy-list file there may be a rename included.
    """
    ret = []
    for item in copyfile:
        # remove leading/trailing whitespace
        item = item.strip()
        # comments
        if not item or item[0] == '#':
            continue
        if item[0] == '/':
            raise Exception("Input path '%s' is absolute path, this isn't allowed" % (item, ))
        if ' -> ' in item:
            srcitem, dstitem = item.split(' -> ')
            if (srcitem[-1] == '/') != (dstitem[-1] == '/'):
                raise Exception("Cannot copy file/dir to dir/file")
        else:
            srcitem = dstitem = item
        ret.append((srcitem, dstitem))
    return ret


def read_dependencies(depfilename):
    """
    Read a (the) dependency file and return the list of
    dependencies as a dictionary, mapping a Kconfig symbol
    to a list of kernel version dependencies.
    
    If a backported feature that an upstream backported driver
    depends on had kconfig limitations (ie, debugging feature not
    available) a built constaint restriction can be expressed
    by using a kconfig expression. The kconfig expressions can
    be specified by using the "kconfig: " prefix.
    
    While reading ignore blank or commented lines.
    """
    ret = {}
    depfile = open(depfilename, 'r')
    for item in depfile:
        kconfig_exp = ""
        item = item.strip()
        if not item or item[0] == '#':
            continue
        if "kconfig:" in item:
            sym, kconfig_exp = item.split(" ", 1)
            if not sym in ret:
                ret[sym] = [kconfig_exp, ]
            else:
                ret[sym].append(kconfig_exp)
        else:
            sym, dep = item.split()
            if not sym in ret:
                ret[sym] = [dep, ]
            else:
                ret[sym].append(dep)
    return ret


def check_output_dir(d, clean):
    """
    Check that the output directory doesn't exist or is empty,
    unless clean is True in which case it's nuked. This helps
    sanity check the output when generating a tree, so usually
    running with --clean isn't suggested.
    """
    if clean:
        shutil.rmtree(d, ignore_errors=True)
    try:
        os.rmdir(d)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


def copytree(src, dst, symlinks=False, ignore=None):
    """
    Copy a directory tree. This differs from shutil.copytree()
    in that it allows destination directories to already exist.
    """
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    if not os.path.isdir(dst):
        os.makedirs(dst)
    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copytree(srcname, dstname, symlinks, ignore)
            else:
                shutil.copy2(srcname, dstname)
        except (IOError, os.error) as why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except shutil.Error as err:
            errors.extend(err.args[0])
    try:
        shutil.copystat(src, dst)
    except WindowsError:
        # can't copy file access times on Windows
        pass
    except OSError as why:
        errors.extend((src, dst, str(why)))
    if errors:
        raise shutil.Error(errors)


def copy_files(srcpath, copy_list, outdir):
    """
    Copy the copy_list files and directories from the srcpath
    to the outdir. The copy_list contains source and target
    names.

    For now, it also ignores any *~ editor backup files, though
    this should probably be generalized (maybe using .gitignore?)
    Similarly the code that only copies some files (*.c, *.h,
    *.awk, Kconfig, Makefile) to avoid any build remnants in the
    kernel if they should exist.
    """
    for srcitem, tgtitem in copy_list:
        if tgtitem == '':
            copytree(srcpath, outdir, ignore=shutil.ignore_patterns('*~'))
        elif tgtitem[-1] == '/':
            def copy_ignore(dir, entries):
                r = []
                for i in entries:
                    if i[-2:] == '.o' or i[-1] == '~':
                        r.append(i)
                return r
            copytree(os.path.join(srcpath, srcitem),
                     os.path.join(outdir, tgtitem),
                     ignore=copy_ignore)
        else:
            try:
                os.makedirs(os.path.join(outdir, os.path.dirname(tgtitem)))
            except OSError as e:
                # ignore dirs we might have created just now
                if e.errno != errno.EEXIST:
                    raise
            shutil.copy(os.path.join(srcpath, srcitem),
                        os.path.join(outdir, tgtitem))


def copy_git_files(srcpath, copy_list, rev, outdir):
    """
    "Copy" files from a git repository. This really means listing them with
    ls-tree and then using git show to obtain all the blobs.
    """
    for srcitem, tgtitem in copy_list:
        for m, t, h, f in git.ls_tree(rev=rev, files=(srcitem,), tree=srcpath):
            assert t == 'blob'
            f = os.path.join(outdir, f.replace(srcitem, tgtitem))
            d = os.path.dirname(f)
            if not os.path.exists(d):
                os.makedirs(d)
            outf = open(f, 'w')
            git.get_blob(h, outf, tree=srcpath)
            outf.close()
            os.chmod(f, int(m, 8))

def automatic_backport_mangle_c_file(name):
    return name.replace('/', '-')


def add_automatic_backports(args):
    disable_list = []
    export = re.compile(r'^EXPORT_SYMBOL(_GPL)?\((?P<sym>[^\)]*)\)')
    bpi = kconfig.get_backport_info(os.path.join(args.bpid.target_dir, 'compat', 'Kconfig'))
    configtree = kconfig.ConfigTree(os.path.join(args.bpid.target_dir, 'Kconfig'), args.bpid)
    ignore=['Kconfig.kernel', 'Kconfig.versions']
    configtree.verify_sources(ignore=ignore)
    git_debug_snapshot(args, "verify sources for automatic backports")
    all_selects = configtree.all_selects()
    for sym, vals in bpi.items():
        if sym.startswith('BPAUTO_BUILD_'):
            if not sym[13:] in all_selects:
                disable_list.append(sym)
                continue
        symtype, module_name, c_files, h_files = vals

        # first copy files
        files = []
        for f in c_files:
            files.append((f, os.path.join('compat', automatic_backport_mangle_c_file(f))))
        for f in h_files:
            files.append((os.path.join('include', f),
                          os.path.join('include', os.path.dirname(f), 'backport-' + os.path.basename(f))))
        if args.git_revision:
            copy_git_files(args.kerneldir, files, args.git_revision, args.bpid.target_dir)
        else:
            copy_files(args.kerneldir, files, args.bpid.target_dir)

        # now add the Makefile line
        mf = open(os.path.join(args.bpid.target_dir, 'compat', 'Makefile'), 'a+')
        o_files = [automatic_backport_mangle_c_file(f)[:-1] + 'o' for f in c_files]
        if symtype == 'tristate':
            if not module_name:
                raise Exception('backporting a module requires a #module-name')
            for of in o_files:
                mf.write('%s-objs += %s\n' % (module_name, of))
            mf.write('obj-$(%s%s) += %s.o\n' % (args.bpid.full_prefix, sym, module_name))
        elif symtype == 'bool':
            mf.write('compat-$(%s%s) += %s\n' % (args.bpid.full_prefix, sym, ' '.join(o_files)))

        # finally create the include file
        syms = []
        for f in c_files:
            for l in open(os.path.join(args.bpid.target_dir, 'compat',
                                       automatic_backport_mangle_c_file(f)), 'r'):
                m = export.match(l)
                if m:
                    syms.append(m.group('sym'))
        for f in h_files:
            outf = open(os.path.join(args.bpid.target_dir, 'include', f), 'w')
            outf.write('/* Automatically created during backport process */\n')
            outf.write('#ifndef %s%s\n' % (args.bpid.full_prefix, sym))
            outf.write('#include_next <%s>\n' % f)
            outf.write('#else\n');
            for s in syms:
                outf.write('#undef %s\n' % s)
                outf.write('#define %s LINUX_BACKPORT(%s)\n' % (s, s))
            outf.write('#include <%s>\n' % (os.path.dirname(f) + '/backport-' + os.path.basename(f), ))
            outf.write('#endif /* %s%s */\n' % (args.bpid.full_prefix, sym))
    return disable_list

def git_debug_init(args):
    """
    Initialize a git repository in the output directory and commit the current
    code in it. This is only used for debugging the transformations this code
    will do to the output later.
    """
    if not args.gitdebug:
        return
    # Git supports re-initialization, although not well documented it can
    # reset config stuff, lets avoid that if the tree already exists.
    if not os.path.exists(os.path.join(args.bpid.project_dir, '.git')):
        git.init(tree=args.bpid.project_dir)
    git.commit_all("Copied backport", tree=args.bpid.project_dir)


def git_debug_snapshot(args, name):
    """
    Take a git snapshot for the debugging.
    """
    if not args.gitdebug:
        return
    git.commit_all(name, tree=args.bpid.project_dir)

def get_rel_spec_stable(rel):
    """
    Returns release specs for a linux-stable backports based release.
    """
    if ("rc" in rel):
        m = re.match(r"(?P<VERSION>\d+)\.+" \
                     "(?P<PATCHLEVEL>\d+)[.]*" \
                     "(?P<SUBLEVEL>\d*)" \
                     "[-rc]+(?P<RC_VERSION>\d+)\-+" \
                     "(?P<RELMOD_UPDATE>\d+)[-]*" \
                     "(?P<RELMOD_TYPE>[usnpc]*)", \
                     rel)
    else:
        m = re.match(r"(?P<VERSION>\d+)\.+" \
                     "(?P<PATCHLEVEL>\d+)[.]*" \
                     "(?P<SUBLEVEL>\d*)\-+" \
                     "(?P<RELMOD_UPDATE>\d+)[-]*" \
                     "(?P<RELMOD_TYPE>[usnpc]*)", \
                     rel)
    if (not m):
        return m
    return m.groupdict()

def get_rel_spec_next(rel):
    """
    Returns release specs for a linux-next backports based release.
    """
    m = re.match(r"(?P<DATE_VERSION>\d+)[-]*" \
                 "(?P<RELMOD_UPDATE>\d*)[-]*" \
                 "(?P<RELMOD_TYPE>[usnpc]*)", \
                 rel)
    if (not m):
        return m
    return m.groupdict()

def get_rel_prep(rel):
    """
    Returns a dict with prep work details we need prior to
    uploading a backports release to kernel.org
    """
    rel_specs = get_rel_spec_stable(rel)
    is_stable = True
    rel_tag = ""
    paths = list()
    if (not rel_specs):
        rel_specs = get_rel_spec_next(rel)
        if (not rel_specs):
            sys.stdout.write("rel: %s\n" % rel)
            return None
        if (rel_specs['RELMOD_UPDATE'] == '0' or
            rel_specs['RELMOD_UPDATE'] == '1'):
            return None
        is_stable = False
        date = rel_specs['DATE_VERSION']
        year = date[0:4]
        if (len(year) != 4):
            return None
        month = date[4:6]
        if (len(month) != 2):
            return None
        day = date[6:8]
        if (len(day) != 2):
            return None
        paths.append(year)
        paths.append(month)
        paths.append(day)
        rel_tag = "backports-" + rel.replace(rel_specs['RELMOD_TYPE'], "")
    else:
        ignore = "-"
        if (not rel_specs['RELMOD_UPDATE']):
            return None
        if (rel_specs['RELMOD_UPDATE'] == '0'):
            return None
        ignore += rel_specs['RELMOD_UPDATE']
        if (rel_specs['RELMOD_TYPE'] != ''):
            ignore += rel_specs['RELMOD_TYPE']
        base_rel = rel.replace(ignore, "")
        paths.append("v" + base_rel)
        rel_tag = "v" + rel.replace(rel_specs['RELMOD_TYPE'], "")

    rel_prep = dict(stable = is_stable,
                    expected_tag = rel_tag,
                    paths_to_create = paths)
    return rel_prep

def create_tar_and_gz(tar_name, dir_to_tar):
    """
    We need both a tar file and gzip for kernel.org, the tar file
    gets signed, then we upload the compressed version, kup-server
    in the backend decompresses and verifies the tarball against
    our signature.
    """
    basename = os.path.basename(dir_to_tar)
    tar = tarfile.open(tar_name, "w")
    tar.add(dir_to_tar, basename)
    tar.close()

    tar_file = open(tar_name, "r")

    gz_file = gzip.GzipFile(tar_name + ".gz", 'wb')
    gz_file.write(tar_file.read())
    gz_file.close()

def upload_release(args, rel_prep, logwrite=lambda x:None):
    """
    Given a path of a relase make tarball out of it, PGP sign it, and
    then upload it to kernel.org using kup.

    The linux-next based release do not require a RELMOD_UPDATE
    given that typically only one release is made per day. Using
    RELMOD_UPDATE for these releases is allowed though and if
    present it must be > 1.

    The linux-stable based releases require a RELMOD_UPDATE.

    RELMOD_UPDATE must be numeric and > 0 just as the RC releases
    of the Linux kernel.

    The tree must also be tagged with the respective release, without
    the RELMOD_TYPE. For linux-next based releases this consists of
    backports- followed by DATE_VERSION and if RELMOD_TYPE is present.
    For linux-stable releases this consists of v followed by the
    full release version except the RELMOD_TYPE.

    Uploads will not be allowed if these rules are not followed.
    """
    korg_path = "/pub/linux/kernel/projects/backports"

    if (rel_prep['stable']):
        korg_path += "/stable"

    parent = os.path.dirname(args.bpid.project_dir)
    release = os.path.basename(args.bpid.project_dir)
    tar_name = parent + '/' + release + ".tar"
    gzip_name = tar_name + ".gz"

    create_tar_and_gz(tar_name, args.bpid.project_dir)

    logwrite(gpg.sign(tar_name, extra_args=['--armor', '--detach-sign']))

    logwrite("------------------------------------------------------")

    if (not args.kup_test):
        logwrite("About to upload, current target path contents:")
    else:
        logwrite("kup-test: current target path contents:")

    logwrite(kup.ls(path=korg_path))

    for path in rel_prep['paths_to_create']:
        korg_path += '/' + path
        if (not args.kup_test):
            logwrite("create directory: %s" % korg_path)
            logwrite(kup.mkdir(korg_path))
    korg_path += '/'
    if (not args.kup_test):
        logwrite("upload file %s to %s" % (gzip_name, korg_path))
        logwrite(kup.put(gzip_name, tar_name + '.asc', korg_path))
        logwrite("\nFinished upload!\n")
        logwrite("Target path contents:")
        logwrite(kup.ls(path=korg_path))
    else:
        kup_cmd = "kup put /\n\t\t%s /\n\t\t%s /\n\t\t%s" % (gzip_name, tar_name + '.asc', korg_path)
        logwrite("kup-test: skipping cmd: %s" % kup_cmd)

def apply_patches(args, desc, source_dir, patch_src, target_dir, logwrite=lambda x:None):
    """
    Given a path of a directories of patches and SmPL patches apply
    them on the target directory. If requested refresh patches, or test
    a specific SmPL patch.
    """
    logwrite('Applying patches from %s to %s ...' % (patch_src, target_dir))
    test_cocci = args.test_cocci or args.profile_cocci
    test_cocci_found = False
    patches = []
    sempatches = []
    for root, dirs, files in os.walk(os.path.join(source_dir, patch_src)):
        for f in files:
            if not test_cocci and f.endswith('.patch'):
                patches.append(os.path.join(root, f))
            if f.endswith('.cocci'):
                if test_cocci:
                    if f not in test_cocci:
                        continue
                    test_cocci_found = True
                    if args.test_cocci:
                        logwrite("Testing Coccinelle SmPL patch: %s" % test_cocci)
                    elif args.profile_cocci:
                        logwrite("Profiling Coccinelle SmPL patch: %s" % test_cocci)
                sempatches.append(os.path.join(root, f))
    patches.sort()
    prefix_len = len(os.path.join(source_dir, patch_src)) + 1
    for pfile in patches:
        print_name = pfile[prefix_len:]
        # read the patch file
        p = patch.fromfile(pfile)
        # complain if it's not a patch
        if not p:
            raise Exception('No patch content found in %s' % print_name)
        # leading / seems to be stripped?
        if 'dev/null' in p.items[0].source:
            raise Exception('Patches creating files are not supported (in %s)' % print_name)
        # check if the first file the patch touches exists, if so
        # assume the patch needs to be applied -- otherwise continue
        patched_file = '/'.join(p.items[0].source.split('/')[1:])
        fullfn = os.path.join(target_dir, patched_file)
        if not os.path.exists(fullfn):
            if args.verbose:
                logwrite("Not applying %s, not needed" % print_name)
            continue
        if args.verbose:
            logwrite("Applying patch %s" % print_name)

        if args.refresh:
            # but for refresh, of course look at all files the patch touches
            for patchitem in p.items:
                patched_file = '/'.join(patchitem.source.split('/')[1:])
                fullfn = os.path.join(target_dir, patched_file)
                shutil.copyfile(fullfn, fullfn + '.orig_file')

        process = subprocess.Popen(['patch', '-p1'], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                                   close_fds=True, universal_newlines=True,
                                   cwd=target_dir)
        output = process.communicate(input=open(pfile, 'r').read())[0]
        output = output.split('\n')
        if output[-1] == '':
            output = output[:-1]
        if args.verbose:
            for line in output:
                logwrite('> %s' % line)
        if process.returncode != 0:
            if not args.verbose:
                logwrite("Failed to apply changes from %s" % print_name)
                for line in output:
                    logwrite('> %s' % line)
            raise Exception('Patch failed')

        if args.refresh:
            pfilef = open(pfile + '.tmp', 'a')
            pfilef.write(p.top_header)
            pfilef.flush()
            for patchitem in p.items:
                patched_file = '/'.join(patchitem.source.split('/')[1:])
                fullfn = os.path.join(target_dir, patched_file)
                process = subprocess.Popen(['diff', '-p', '-u', patched_file + '.orig_file', patched_file,
                                            '--label', 'a/' + patched_file,
                                            '--label', 'b/' + patched_file],
                                           stdout=pfilef, close_fds=True,
                                           universal_newlines=True, cwd=target_dir)
                process.wait()
                os.unlink(fullfn + '.orig_file')
                if not process.returncode in (0, 1):
                    logwrite("Failed to diff to refresh %s" % print_name)
                    pfilef.close()
                    os.unlink(pfile + '.tmp')
                    raise Exception('Refresh failed')
            pfilef.close()
            os.rename(pfile + '.tmp', pfile)

        # remove orig/rej files that patch sometimes creates
        for root, dirs, files in os.walk(target_dir):
            for f in files:
                if f[-5:] == '.orig' or f[-4:] == '.rej':
                    os.unlink(os.path.join(root, f))
        git_debug_snapshot(args, "apply %s patch %s" % (desc, print_name))

    sempatches.sort()
    prefix_len = len(os.path.join(source_dir, patch_src)) + 1

    for cocci_file in sempatches:
        # Until Coccinelle picks this up
        pycocci = os.path.join(source_dir, 'devel/pycocci')
        cmd = [pycocci, cocci_file]
        extra_spatch_args = []
        if args.profile_cocci:
            cmd.append('--profile-cocci')
        cmd.append(os.path.abspath(target_dir))
        print_name = cocci_file[prefix_len:]
        if args.verbose:
            logwrite("Applying SmPL patch %s" % print_name)
        sprocess = subprocess.Popen(cmd,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    close_fds=True, universal_newlines=True,
                                    cwd=target_dir)
        output = sprocess.communicate()[0]
        sprocess.wait()
        if sprocess.returncode != 0:
            logwrite("Failed to process SmPL patch %s" % print_name)
            raise Exception('SmPL patch failed')
        output = output.split('\n')
        if output[-1] == '':
            output = output[:-1]
        if args.verbose:
            for line in output:
                logwrite('> %s' % line)

        # remove cocci_backup files
        for root, dirs, files in os.walk(target_dir):
            for f in files:
                if f.endswith('.cocci_backup'):
                    os.unlink(os.path.join(root, f))
        git_debug_snapshot(args, "apply %s SmPL patch %s" % (desc, print_name))

    if test_cocci and test_cocci_found:
        logwrite('Done!')
        sys.exit(0)

def _main():
    # Our binary requirements go here
    req = reqs.Req()
    req.require('git')
    req.coccinelle('1.0.0-rc21')
    if not req.reqs_match():
        sys.exit(1)

    # set up and parse arguments
    parser = argparse.ArgumentParser(description='generate backport tree')
    parser.add_argument('kerneldir', metavar='<kernel tree>', type=str,
                        help='Kernel tree to copy drivers from')
    parser.add_argument('outdir', metavar='<output directory>', type=str,
                        help='Directory to write the generated tree to')
    parser.add_argument('--copy-list', metavar='<listfile>', type=argparse.FileType('r'),
                        default='copy-list',
                        help='File containing list of files/directories to copy, default "copy-list"')
    parser.add_argument('--git-revision', metavar='<revision>', type=str,
                        help='git commit revision (see gitrevisions(7)) to take objects from.' +
                             'If this is specified, the kernel tree is used as git object storage ' +
                             'and we use git ls-tree to get the files.')
    parser.add_argument('--clean', const=True, default=False, action="store_const",
                        help='Clean output directory instead of erroring if it isn\'t empty')
    parser.add_argument('--integrate', const=True, default=False, action="store_const",
                        help='Integrate a future backported kernel solution into ' +
                             'an older kernel tree source directory.')
    parser.add_argument('--refresh', const=True, default=False, action="store_const",
                        help='Refresh patches as they are applied, the source dir will be modified!')
    parser.add_argument('--base-name', metavar='<name>', type=str, default='Linux',
                        help='name of base tree, default just "Linux"')
    parser.add_argument('--gitdebug', const=True, default=False, action="store_const",
                        help='Use git, in the output tree, to debug the various transformation steps ' +
                             'that the tree generation makes (apply patches, ...)')
    parser.add_argument('--verbose', const=True, default=False, action="store_const",
                        help='Print more verbose information')
    parser.add_argument('--extra-driver', nargs=2, metavar=('<source dir>', '<copy-list>'), type=str,
                        action='append', default=[], help='Extra driver directory/copy-list.')
    parser.add_argument('--kup', const=True, default=False, action="store_const",
                        help='For maintainers: upload a release to kernel.org')
    parser.add_argument('--kup-test', const=True, default=False, action="store_const",
                        help='For maintainers: do all the work as if you were about to ' +
                             'upload to kernel.org but do not do the final `kup put` ' +
                             'and also do not run any `kup mkdir` commands. This will ' +
                             'however run `kup ls` on the target paths so ' +
                             'at the very least we test your kup configuration. ' +
                             'If this is your first time uploading use this first!')
    parser.add_argument('--test-cocci', metavar='<sp_file>', type=str, default=None,
                        help='Only use the cocci file passed for Coccinelle, don\'t do anything else, ' +
                             'also creates a git repo on the target directory for easy inspection ' +
                             'of changes done by Coccinelle.')
    parser.add_argument('--profile-cocci', metavar='<sp_file>', type=str, default=None,
                        help='Only use the cocci file passed and pass --profile  to Coccinelle, ' +
                             'also creates a git repo on the target directory for easy inspection ' +
                             'of changes done by Coccinelle.')
    args = parser.parse_args()

    # When building a package we use CPTCFG as we can rely on the
    # fact that kconfig treats CONFIG_ as an environment variable
    # requring less changes on code. For kernel integration we use
    # the longer CONFIG_BACKPORT given that we'll be sticking to
    # the kernel symbol namespace, to address that we do a final
    # search / replace. Technically its possible to rely on the
    # same prefix for packaging as with kernel integration but
    # there are already some users of the CPTCFG prefix.
    bpid = None
    if args.integrate:
        bpid = Bp_Identity(integrate = args.integrate,
                           kconfig_prefix = 'CONFIG_',
                           project_prefix = 'BACKPORT_',
                           project_dir = args.outdir,
                           target_dir = os.path.join(args.outdir, 'backports/'),
                           target_dir_name = 'backports/',
                           kconfig_source_var = '$BACKPORT_DIR',
                           )
    else:
        bpid = Bp_Identity(integrate = args.integrate,
                           kconfig_prefix = 'CPTCFG_',
                           project_prefix = '',
                           project_dir = args.outdir,
                           target_dir = args.outdir,
                           target_dir_name = '',
                           kconfig_source_var = '$BACKPORT_DIR',
                           )

    def logwrite(msg):
        sys.stdout.write(msg)
        sys.stdout.write('\n')
        sys.stdout.flush()

    return process(args.kerneldir, args.copy_list,
                   git_revision=args.git_revision,
                   bpid=bpid,
                   clean=args.clean,
                   refresh=args.refresh, base_name=args.base_name,
                   gitdebug=args.gitdebug, verbose=args.verbose,
                   extra_driver=args.extra_driver,
                   kup=args.kup,
                   kup_test=args.kup_test,
                   test_cocci=args.test_cocci,
                   profile_cocci=args.profile_cocci,
                   logwrite=logwrite)

def process(kerneldir, copy_list_file, git_revision=None,
            bpid=None,
            clean=False, refresh=False, base_name="Linux", gitdebug=False,
            verbose=False, extra_driver=[], kup=False,
            kup_test=False,
            test_cocci=None,
            profile_cocci=None,
            logwrite=lambda x:None,
            git_tracked_version=False):
    class Args(object):
        def __init__(self, kerneldir, copy_list_file,
                     git_revision, bpid, clean, refresh, base_name,
                     gitdebug, verbose, extra_driver, kup,
                     kup_test,
                     test_cocci,
                     profile_cocci):
            self.kerneldir = kerneldir
            self.copy_list = copy_list_file
            self.git_revision = git_revision
            self.bpid = bpid
            self.clean = clean
            self.refresh = refresh
            self.base_name = base_name
            self.gitdebug = gitdebug
            self.verbose = verbose
            self.extra_driver = extra_driver
            self.kup = kup
            self.kup_test = kup_test
            self.test_cocci = test_cocci
            self.profile_cocci = profile_cocci
            if self.test_cocci or self.profile_cocci:
                self.gitdebug = True
    def git_paranoia(tree=None, logwrite=lambda x:None):
        data = git.paranoia(tree)
        if (data['r'] != 0):
            logwrite('Cannot use %s' % tree)
            logwrite('%s' % data['output'])
            sys.exit(data['r'])
        else:
            logwrite('Validated tree: %s' % tree)

    args = Args(kerneldir, copy_list_file,
                git_revision, bpid, clean, refresh, base_name,
                gitdebug, verbose, extra_driver, kup, kup_test,
                test_cocci, profile_cocci)
    rel_prep = None

    if bpid.integrate:
        if args.kup_test or args.test_cocci or args.profile_cocci or args.refresh:
            logwrite('Cannot use integration with:\n\tkup_test\n\ttest_cocci\n\tprofile_cocci\n\trefresh\n');
            sys.exit(1)

    # start processing ...
    if (args.kup or args.kup_test):
        git_paranoia(source_dir, logwrite)
        git_paranoia(kerneldir, logwrite)

        rel_describe = git.describe(rev=None, tree=source_dir, extra_args=['--dirty'])
        release = os.path.basename(bpid.target_dir)
        version = release.replace("backports-", "")

        rel_prep = get_rel_prep(version)
        if (not rel_prep):
            logwrite('Invalid backports release name: %s' % release)
            logwrite('For rules on the release name see upload_release()')
            sys.exit(1)
        rel_type = "linux-stable"
        if (not rel_prep['stable']):
            rel_type = "linux-next"
        if (rel_prep['expected_tag'] != rel_describe):
            logwrite('Unexpected %s based backports release tag on' % rel_type)
            logwrite('the backports tree tree: %s\n' % rel_describe)
            logwrite('You asked to make a release with this ')
            logwrite('directory name: %s' % release)
            logwrite('The actual expected tag we should find on')
            logwrite('the backports tree then is: %s\n' % rel_prep['expected_tag'])
            logwrite('For rules on the release name see upload_release()')
            sys.exit(1)

    copy_list = read_copy_list(args.copy_list)
    deplist = read_dependencies(os.path.join(source_dir, 'dependencies'))

    # validate output directory
    check_output_dir(bpid.target_dir, args.clean)

    # do the copy
    backport_integrate_files = [
            ('Makefile.kernel', 'Makefile'),
            ('Kconfig.integrate', 'Kconfig'),
            ]
    backport_package_files = [(x, x) for x in [
        'Makefile',
        'kconf/',
        'Makefile.real',
        'Makefile.kernel',
        'Kconfig.package.hacks',
        'scripts/',
        '.blacklist.map',
        '.gitignore',
        'Makefile.build'] ]
    backport_package_files += [
            ('Kconfig.package', 'Kconfig'),
            ]
    backport_files = [(x, x) for x in [
        'Kconfig.sources',
        'compat/',
        'backport-include/',
        'unload.sh',
    ]]

    if not bpid.integrate:
        backport_files += backport_package_files
    else:
        backport_files += backport_integrate_files

    if not args.git_revision:
        logwrite('Copy original source files ...')
    else:
        logwrite('Get original source files from git ...')
    
    copy_files(os.path.join(source_dir, 'backport'), backport_files, bpid.target_dir)

    git_debug_init(args)

    if not args.git_revision:
        copy_files(args.kerneldir, copy_list, bpid.target_dir)
    else:
        copy_git_files(args.kerneldir, copy_list, args.git_revision, bpid.target_dir)

    # FIXME: should we add a git version of this (e.g. --git-extra-driver)?
    for src, copy_list in args.extra_driver:
        if (args.kup or args.kup_test):
            git_paranoia(src)
        copy_files(src, read_copy_list(open(copy_list, 'r')), bpid.target_dir)

    git_debug_snapshot(args, 'Add driver sources')

    disable_list = add_automatic_backports(args)
    if git_tracked_version:
        backports_version = "(see git)"
        kernel_version = "(see git)"
    else:
        backports_version = git.describe(tree=source_dir, extra_args=['--long'])
        kernel_version = git.describe(rev=args.git_revision or 'HEAD',
                                      tree=args.kerneldir,
                                      extra_args=['--long'])

    if not bpid.integrate:
        f = open(os.path.join(bpid.target_dir, 'versions'), 'w')
        f.write('BACKPORTS_VERSION="%s"\n' % backports_version)
        f.write('BACKPORTED_KERNEL_VERSION="%s"\n' % kernel_version)
        f.write('BACKPORTED_KERNEL_NAME="%s"\n' % args.base_name)
        if git_tracked_version:
            f.write('BACKPORTS_GIT_TRACKED="backport tracker ID: $(shell git rev-parse HEAD 2>/dev/null || echo \'not built in git tree\')"\n')
        f.close()
        git_debug_snapshot(args, "add versions files")
    else:
        kconf_regexes = [
                (re.compile(r'.*(?P<key>%%BACKPORT_DIR%%)'), '%%BACKPORT_DIR%%', 'backports/'),
                (re.compile(r'.*(?P<key>%%BACKPORTS_VERSION%%).*'), '%%BACKPORTS_VERSION%%', backports_version),
                (re.compile(r'.*(?P<key>%%BACKPORTED_KERNEL_VERSION%%).*'), '%%BACKPORTED_KERNEL_VERSION%%', kernel_version),
                (re.compile(r'.*(?P<key>%%BACKPORTED_KERNEL_NAME%%).*'), '%%BACKPORTED_KERNEL_NAME%%', args.base_name),
        ]
        out = ''
        for l in open(os.path.join(bpid.target_dir, 'Kconfig'), 'r'):
            for r in kconf_regexes:
                m = r[0].match(l)
                if m:
                    l = re.sub(r'(' + r[1] + ')', r'' + r[2] + '', l)
            out += l
        outf = open(os.path.join(bpid.target_dir, 'Kconfig'), 'w')
        outf.write(out)
        outf.close()
        git_debug_snapshot(args, "modify top level backports/Kconfig with backports identity")

    if disable_list:
        # No need to verify_sources() as compat's Kconfig has no 'source' call
        bpcfg = kconfig.ConfigTree(os.path.join(bpid.target_dir, 'compat', 'Kconfig'), bpid)
        bpcfg.disable_symbols(disable_list)
    git_debug_snapshot(args, 'Add automatic backports')

    apply_patches(args, "backport", source_dir, 'patches', bpid.target_dir, logwrite)

    # Kernel integration requires Kconfig.versions already generated for you,
    # we cannot do this for a package as we have no idea what kernel folks
    # will be using.
    if bpid.integrate:
        kver = gen_version.kernelversion(bpid.project_dir)
        rel_specs = gen_version.get_rel_spec_stable(kver)
        if not rel_specs:
            logwrite('Cannot parse source kernel version, update parser')
            sys.exit(1)
        data = gen_version.genkconfig_versions(rel_specs)
        fo = open(os.path.join(bpid.target_dir, 'Kconfig.versions'), 'w')
        fo.write(data)
        fo.close()
        git_debug_snapshot(args, "generate kernel version requirement Kconfig file")

    # some post-processing is required
    configtree = kconfig.ConfigTree(os.path.join(bpid.target_dir, 'Kconfig'), bpid)
    ignore=['Kconfig.kernel', 'Kconfig.versions']

    configtree.verify_sources(ignore=ignore)
    git_debug_snapshot(args, "verify sources on top level backports Kconfig")

    orig_symbols = configtree.symbols()

    logwrite('Modify Kconfig tree ...')
    configtree.prune_sources(ignore=ignore)
    git_debug_snapshot(args, "prune Kconfig tree")

    if not bpid.integrate:
        configtree.force_tristate_modular()
        git_debug_snapshot(args, "force tristate options modular")

    ignore = [os.path.join(bpid.target_dir, x) for x in [
                'Kconfig.package.hacks',
                'Kconfig.versions',
                'Kconfig',
                ]
            ]
    configtree.adjust_backported_configs(ignore=ignore, orig_symbols=orig_symbols)
    git_debug_snapshot(args, "adjust backports config symbols we port")

    configtree.modify_selects()
    git_debug_snapshot(args, "convert select to depends on")

    symbols = configtree.symbols()

    # write local symbol list -- needed during packaging build
    if not bpid.integrate:
        f = open(os.path.join(bpid.target_dir, '.local-symbols'), 'w')
        for sym in symbols:
            f.write('%s=\n' % sym)
        f.close()
        git_debug_snapshot(args, "add symbols files")

    # add defconfigs that we want
    defconfigs_dir = os.path.join(source_dir, 'backport', 'defconfigs')
    os.mkdir(os.path.join(bpid.target_dir, 'defconfigs'))
    for dfbase in os.listdir(defconfigs_dir):
        copy_defconfig = True
        dfsrc = os.path.join(defconfigs_dir, dfbase)
        for line in open(dfsrc, 'r'):
            if not '=' in line:
                continue
            line_ok = False
            for sym in symbols:
                if sym + '=' in line:
                    line_ok = True
                    break
            if not line_ok:
                copy_defconfig = False
                break
        if copy_defconfig:
            shutil.copy(dfsrc, os.path.join(bpid.target_dir, 'defconfigs', dfbase))

    git_debug_snapshot(args, "add (useful) defconfig files")

    logwrite('Rewrite Makefiles and Kconfig files ...')

    # rewrite Makefile and source symbols

    # symbols we know only we can provide under the backport project prefix
    # for which we need an exception.
    skip_orig_syms = [ bpid.project_prefix + x for x in [
            'INTEGRATE',
            ]
    ]
    parse_orig_syms = [x for x in orig_symbols if x not in skip_orig_syms ]
    regexes = []
    for some_symbols in [parse_orig_syms[i:i + 50] for i in range(0, len(parse_orig_syms), 50)]:
        r = 'CONFIG_((' + '|'.join([s + '(_MODULE)?' for s in some_symbols]) + ')([^A-Za-z0-9_]|$))'
        regexes.append(re.compile(r, re.MULTILINE))
    for root, dirs, files in os.walk(bpid.target_dir):
        # don't go into .git dir (possible debug thing)
        if '.git' in dirs:
            dirs.remove('.git')
        for f in files:
            data = open(os.path.join(root, f), 'r').read()
            for r in regexes:
                data = r.sub(r'' + bpid.full_prefix + '\\1', data)
            data = re.sub(r'\$\(srctree\)', '$(backport_srctree)', data)
            data = re.sub(r'-Idrivers', '-I$(backport_srctree)/drivers', data)
            if bpid.integrate:
                data = re.sub(r'CPTCFG_', bpid.full_prefix, data)
            fo = open(os.path.join(root, f), 'w')
            fo.write(data)
            fo.close()

    git_debug_snapshot(args, "rename config symbol / srctree usage")

    # disable unbuildable Kconfig symbols and stuff Makefiles that doesn't exist
    if bpid.integrate:
        maketree = make.MakeTree(os.path.join(bpid.target_dir, 'Makefile'))
    else:
        maketree = make.MakeTree(os.path.join(bpid.target_dir, 'Makefile.kernel'))
    disable_kconfig = []
    disable_makefile = []
    for sym in maketree.get_impossible_symbols():
        disable_kconfig.append(sym[7:])
        disable_makefile.append(sym[7:])

    configtree.disable_symbols(disable_kconfig)
    git_debug_snapshot(args, "disable impossible kconfig symbols")

    # add kernel version dependencies to Kconfig, from the dependency list
    # we read previously
    for sym in tuple(deplist.keys()):
        new = []
        for dep in deplist[sym]:
            if "kconfig:" in dep:
                    kconfig_expr = dep.replace('kconfig: ', '')
                    new.append(kconfig_expr)
            elif (dep == "DISABLE"):
                    new.append('BACKPORT_DISABLED_KCONFIG_OPTION')
            else:
                    new.append('!KERNEL_%s' % dep.replace('.', '_'))
        if bpid.integrate:
            deplist[sym] = ["BACKPORT_" + x for x in new]
        else:
            deplist[sym] = new
    configtree.add_dependencies(deplist)
    git_debug_snapshot(args, "add kernel version dependencies")

    # disable things in makefiles that can't be selected and that the
    # build shouldn't recurse into because they don't exist -- if we
    # don't do that then a symbol from the kernel could cause the build
    # to attempt to recurse and fail
    #
    # Note that we split the regex after 50 symbols, this is because of a
    # limitation in the regex implementation (it only supports 100 nested
    # groups -- 50 seemed safer and is still fast)
    regexes = []
    for some_symbols in [disable_makefile[i:i + 50] for i in range(0, len(disable_makefile), 50)]:
        r = '^([^#].*((' + bpid.full_prefix_resafe + '|CONFIG_)(' + '|'.join([s for s in some_symbols]) + ')))'
        regexes.append(re.compile(r, re.MULTILINE))
    for f in maketree.get_makefiles():
        data = open(f, 'r').read()
        for r in regexes:
            data = r.sub(r'#\1', data)
        fo = open(f, 'w')
        fo.write(data)
        fo.close()
    git_debug_snapshot(args, "disable unsatisfied Makefile parts")

    if bpid.integrate:
        f = open(os.path.join(bpid.project_dir, 'Kconfig'), 'a')
        f.write('source "backports/Kconfig"\n')
        f.close()
        git_debug_snapshot(args, "hooked backport to top level Kconfig")

        apply_patches(args, "integration", source_dir, 'integration-patches/',
                      bpid.project_dir, logwrite)

    if (args.kup or args.kup_test):
        req = reqs.Req()
        req.kup()
        if not req.reqs_match():
            sys.exit(1)
        upload_release(args, rel_prep, logwrite=logwrite)

    logwrite('Done!')
    return 0

if __name__ == '__main__':
    ret = _main()
    if ret:
        sys.exit(ret)
