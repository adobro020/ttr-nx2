#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Run the unmodified TTREngine under stock Box64 on arm64 Linux with a virtual
# X server and Mesa software GL (Phase 2, steps 8-10). Runs in
# docker/bench-arm64 with networking disabled (make recon-run), so the engine
# cannot reach TTR's servers and no login is attempted (CLAUDE.md rule 5).
#
#   tools/ref/run-engine.sh NAME
#
# Environment knobs (all optional):
#   RUN_SECONDS=90       how long to let the engine run before stopping it
#   STRACE=none|count|trace
#                        strace from the start: -f -c summary (count), or
#                        file, memory, signal, process and IPC syscalls with
#                        arguments (trace). Never -v: environment strings are
#                        not printed.
#   TRACEME_OK=0|1       with STRACE: make the engine's ptrace(PTRACE_TRACEME)
#                        return 0 (strace -e inject). Without it the engine
#                        sees EPERM (it is already traced) and exits after
#                        about 5 s; with it, it behaves as when untraced.
#                        Attaching later is impossible: PTRACE_TRACEME makes
#                        the parent its tracer. This is what gx must answer
#                        on the console too (docs/recon/engine-91bff107.md).
#   APITRACE=0|1         record GL calls with apitrace (LD_PRELOAD; the
#                        engine exits early when it is set, see the recon doc)
#   PANDA_DEBUG=0|1      extra Panda3D config (PANDA_PRC_DIR/PATH) asking for
#                        debug output; the engine ignores it (kept to show so)
#   DLSYM_LOG=0|1        BOX64_DLSYM_ERROR=1: Box64 logs every dlsym and
#                        glXGetProcAddress lookup the engine makes
#   GLVER=x.y[COMPAT]    MESA_GL_VERSION_OVERRIDE: cap the GL version Mesa
#                        offers, to find the lowest version the engine accepts
#   ALSOFT_LOGLEVEL=3    OpenAL Soft (native, wrapped by Box64) logs the
#                        device it opens: backend, format, rate, buffer sizes
#   DYNAREC=1|0          BOX64_DYNAREC
#   FAKE_SERVER=0|1      set TTR_GAMESERVER to a closed local port and a
#                        placeholder cookie so the engine gets past its
#                        "no cookie" check and tries to connect (locally)
#   HUD=0|1              Mesa GALLIUM_HUD frame counter, values dumped to
#                        hud/ (frames per second, sampled by Mesa)
#   BOX64_LOG=1          passed through to Box64
#
# The game directory is copied into the container first, so ref/game stays
# exactly as the patcher left it and files the engine writes can be listed.
# Output goes to build/recon-run/NAME/ (git-ignored): box64/engine log,
# strace output, screenshots, per-5 s thread count and resident memory,
# files the engine created or changed. Screenshots show the game's own art:
# they stay under build/ and are never committed (CLAUDE.md rule 8).
set -euo pipefail

name=${1:?usage: run-engine.sh NAME}
seconds=${RUN_SECONDS:-90}
strace_mode=${STRACE:-none}
apitrace=${APITRACE:-0}
dynarec=${DYNAREC:-1}
fake_server=${FAKE_SERVER:-0}
hud=${HUD:-0}
traceme_ok=${TRACEME_OK:-0}
panda_debug=${PANDA_DEBUG:-0}
dlsym_log=${DLSYM_LOG:-0}
glver=${GLVER:-}

root=$PWD
out=$root/build/recon-run/$name
stage=$root/build/box64-bench/stage
box64=$root/build/box64-bench/box64
[ -x "$box64" ] || { echo "run-engine: build Box64 first (make box64-bench)" >&2; exit 1; }
[ -f "$root/ref/game/TTREngine" ] || { echo "run-engine: no ref/game/TTREngine (make fetch-game)" >&2; exit 1; }
rm -rf "$out"; mkdir -p "$out"

game=/tmp/game
cp -a "$root/ref/game" "$game"
# launcher.py __start_game adds the execute bits before starting the engine;
# do the same on the copy (the patcher writes files without them).
chmod a+x "$game/TTREngine"
(cd "$game" && find . -type f -printf '%P %s %T@\n' | sort) > "$out/files-before.txt"

# --- X server -----------------------------------------------------------------
export DISPLAY=:99
Xvfb :99 -screen 0 1280x720x24 -nolisten tcp >"$out/xvfb.log" 2>&1 &
xvfb=$!
for _ in $(seq 50); do xdpyinfo >/dev/null 2>&1 && break; sleep 0.1; done
xdpyinfo | grep -E 'dimensions|depths' > "$out/display.txt" || true
glxinfo -B > "$out/glxinfo-native.txt" 2>&1 || true

# --- engine environment ---------------------------------------------------------
export LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe
if [ "$hud" = 1 ]; then
    mkdir -p "$out/hud"
    export GALLIUM_HUD=fps GALLIUM_HUD_PERIOD=1 GALLIUM_HUD_DUMP_DIR=$out/hud
fi
export BOX64_LOG=${BOX64_LOG:-1}
[ "$dlsym_log" = 1 ] && export BOX64_DLSYM_ERROR=1
[ -n "$glver" ] && export MESA_GL_VERSION_OVERRIDE=$glver
[ -n "${ALSOFT_LOGLEVEL:-}" ] && export ALSOFT_LOGLEVEL
export BOX64_DYNAREC=$dynarec
export BOX64_RCFILE=$stage/etc/box64.box64rc
export BOX64_LD_LIBRARY_PATH=$stage/usr/lib/box64-x86_64-linux-gnu
unset TTR_GAMESERVER TTR_PLAYCOOKIE
if [ "$fake_server" = 1 ]; then
    # Port 9 on loopback: nothing listens there (network is off anyway).
    # The cookie is a placeholder, never a real credential.
    placeholder="placeholder-not-a-cookie"
    export TTR_GAMESERVER=127.0.0.1:9
    export TTR_PLAYCOOKIE="$placeholder"
fi

if [ "$panda_debug" = 1 ]; then
    mkdir -p /tmp/prc
    printf '%s\n' 'notify-level-glgsg debug' 'notify-level-display debug' \
        'notify-level-glxdisplay debug' 'notify-level-audio debug' \
        'notify-level-openal debug' > /tmp/prc/zz-recon.prc
    export PANDA_PRC_DIR=/tmp/prc PANDA_PRC_PATH=/tmp/prc
fi

# arch_prctl is an x86-64 call: Box64 emulates it, the arm64 host never sees
# it. strace here shows the host (arm64) syscalls, which is what gx serves.
traced='%file,%memory,%signal,%process,%ipc,prctl,rseq,set_robust_list,ptrace'
inject=()
[ "$traceme_ok" = 1 ] && inject=(-e inject=ptrace:retval=0)
cmd=("$box64" ./TTREngine)
case "$strace_mode" in
    none) ;;
    count) cmd=(strace -f -c -S calls -o "$out/strace-count.txt" "${inject[@]}" "${cmd[@]}") ;;
    trace) cmd=(strace -f -tt -s 64 -o "$out/strace-trace.txt" -e "trace=$traced,ptrace"
                "${inject[@]}" "${cmd[@]}") ;;
    *) echo "run-engine: STRACE=$strace_mode?" >&2; exit 2 ;;
esac
if [ "$apitrace" = 1 ]; then
    cmd=(apitrace trace --api gl --output "$out/engine.trace" "${cmd[@]}")
fi

echo "run-engine: $name: ${cmd[*]} (for ${seconds}s, DYNAREC=$dynarec)" | tee "$out/command.txt"
cd "$game"
start=$(date +%s.%N)
"${cmd[@]}" >"$out/engine.log" 2>&1 &
launcher_pid=$!

# Sample the box64 process: thread count, resident and peak memory, CPU time.
(
    clk=$(getconf CLK_TCK)
    echo "t_s threads vmrss_kb vmhwm_kb utime_s stime_s"
    while kill -0 "$launcher_pid" 2>/dev/null; do
        pid=$(pgrep -n -x TTREngine || true)
        if [ -n "$pid" ] && [ -r "/proc/$pid/status" ]; then
            thr=$(awk '/^Threads:/ {print $2}' "/proc/$pid/status")
            rss=$(awk '/^VmRSS:/ {print $2}' "/proc/$pid/status")
            hwm=$(awk '/^VmHWM:/ {print $2}' "/proc/$pid/status")
            read -r ut st < <(awk '{print $14, $15}' "/proc/$pid/stat")
            now=$(date +%s.%N)
            printf '%.0f %s %s %s %.2f %.2f\n' "$(echo "$now - $start" | bc)" \
                "$thr" "$rss" "$hwm" "$(echo "$ut / $clk" | bc -l)" "$(echo "$st / $clk" | bc -l)"
            [ -r "/proc/$pid/maps" ] && cp "/proc/$pid/maps" "$out/maps-last.txt" 2>/dev/null || true
        fi
        sleep 5
    done
) > "$out/samples.txt" 2>/dev/null &
sampler=$!

shot() {
    xwd -root -silent | xwdtopnm 2>/dev/null | pnmtopng > "$out/screen-$1.png" 2>/dev/null || true
}
for t in 10 30 60 "$seconds"; do
    [ "$t" -le "$seconds" ] || continue
    while [ "$(echo "$(date +%s.%N) - $start < $t" | bc)" = 1 ] && kill -0 "$launcher_pid" 2>/dev/null; do
        sleep 1
    done
    kill -0 "$launcher_pid" 2>/dev/null || break
    shot "${t}s"
done
xwininfo -root -tree > "$out/windows.txt" 2>&1 || true

# Per-thread CPU time and the signal masks, just before stopping the engine.
pid=$(pgrep -n -x TTREngine || true)
if [ -n "$pid" ]; then
    grep -E '^(Sig|Shd)(Blk|Ign|Cgt|Pnd)|^TracerPid' "/proc/$pid/status" > "$out/signals.txt" || true
    for t in /proc/"$pid"/task/*; do
        printf '%s %s\n' "$(cat "$t/comm")" "$(awk '{print $14, $15}' "$t/stat")"
    done | sort | awk -v clk="$(getconf CLK_TCK)" '
        {n[$1]++; u[$1]+=$(NF-1); s[$1]+=$NF}
        END {print "thread_name count utime_s stime_s";
             for (k in n) printf "%s %d %.2f %.2f\n", k, n[k], u[k]/clk, s[k]/clk}' \
        > "$out/threads.txt" || true
fi

status=running
if kill -0 "$launcher_pid" 2>/dev/null; then
    pkill -TERM -x TTREngine || true
    sleep 3
    pkill -KILL -x TTREngine || true
else
    status=exited
fi
rc=0
wait "$launcher_pid" 2>/dev/null || rc=$?   # 143 = stopped by SIGTERM above
wait "$sampler" 2>/dev/null || true
end=$(date +%s.%N)
printf 'state_at_stop=%s exit_status=%s wall_s=%.1f\n' "$status" "$rc" \
    "$(echo "$end - $start" | bc)" | tee "$out/result.txt"

(cd "$game" && find . -type f -printf '%P %s %T@\n' | sort) > "$out/files-after.txt"
diff "$out/files-before.txt" "$out/files-after.txt" | grep -E '^[<>]' > "$out/files-changed.txt" || true
mkdir -p "$out/game-files"
for f in logs settings.json .crashreport; do
    [ -e "$game/$f" ] && cp -a "$game/$f" "$out/game-files/" || true
done
if [ "$fake_server" = 1 ]; then
    # Does the engine write the cookie anywhere? (placeholder value only)
    hits=$(grep -rIl -- "$placeholder" "$out" "$game" 2>/dev/null | grep -v '/command.txt$' || true)
    echo "${hits:-none}" > "$out/placeholder-cookie-found-in.txt"
fi
kill "$xvfb" 2>/dev/null || true
echo "run-engine: output in build/recon-run/$name"
