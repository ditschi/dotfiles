# Sourced by each config's setup: copy files, then time the first start until
# every deferred plugin is loaded (this includes downloading plugins).
emulate -L zsh -o err_return -o extended_glob
zmodload zsh/datetime
local cfg_dir=${1:A}
# SPIKE_COMMON_FILES limits the shared files (the baseline only gets the marker)
if (( ${+SPIKE_COMMON_FILES} )); then
  local f
  for f in $SPIKE_COMMON_FILES; do
    mkdir -p -- ~/${f:h}
    cp -- ${cfg_dir:h}/_common/skel/$f ~/$f
  done
else
  cp -r -- ${cfg_dir:h}/_common/skel/*(D) ~/
fi
cp -r -- $cfg_dir/skel/*(D) ~/
(( ${+SPIKE_SETUP_HOOK} )) && eval $SPIKE_SETUP_HOOK
local -F t0=EPOCHREALTIME
# stdin stays open (fifo) so the shell does not see EOF before it is loaded
local fifo=$(mktemp -u) sp
mkfifo -- $fifo
sleep 600 >$fifo &
sp=$!
# like zsh-bench; zinit stalls with TERM unset/unknown; timeout exit 124 means "never fully loaded"
local rc=0
TERM=xterm-256color SPIKE_EXIT_WHEN_LOADED=1 timeout 300 script -qfec 'zsh -li' /dev/null <$fifo >/dev/null 2>&1 || rc=$?
kill $sp 2>/dev/null || true
local -F t1=EPOCHREALTIME
print -r -- "install_ms=$(( (t1 - t0) * 1000 ))"
print -r -- "install_rc=$rc"

# Warm runs (plugins installed, caches built): time to first prompt and to fully loaded.
local report=$(mktemp) n=13
if (( rc == 124 )); then
  print -r -- "warm runs skipped: never fully loaded"
  n=0
fi
repeat $n; do
  sleep 600 >$fifo &
  sp=$!
  SPIKE_T0=$EPOCHREALTIME SPIKE_REPORT=$report TERM=xterm-256color SPIKE_EXIT_WHEN_LOADED=1 \
    timeout 60 script -qfec 'zsh -li' /dev/null <$fifo >/dev/null 2>&1 || true
  kill $sp 2>/dev/null || true
done
rm -f -- $fifo
local line
for line in ${(f)"$(<$report)"}; print -r -- "warm: $line"
rm -f -- $report
