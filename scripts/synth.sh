#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

mapper="-abc9"
flags=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        -nb|--no-bram) flags="$flags -nobram" ;;
        -nd|--no-dsp)  flags="$flags -nodsp" ;;
        -f|--flatten)  flags="$flags -flatten" ;;
        -r|--retime)   mapper="-retime" ;;
        *)
            echo "usage: $0 [-nb|--no-bram] [-nd|--no-dsp] [-f|--flatten] [-r|--retime]" >&2
            exit 2
            ;;
    esac
    shift
done

log="$(mktemp)"
report="$(mktemp)"
check_log="$(mktemp)"
trap 'rm -f "$log" "$report" "$check_log"' EXIT

check_status=0
veryl check >"$check_log" 2>&1 || check_status=$?
sed '/^\[INFO \]/d' "$check_log"
[ "$check_status" -eq 0 ] || exit "$check_status"

veryl build --quiet

if ! yosys -q -m slang -p "
    read_slang -F tinymoa.f --top tinymoa_ecore_top;
    synth_xilinx -family xc7 -top tinymoa_ecore_top $mapper $flags;
    tee -o $report stat -tech xilinx
" >"$log" 2>&1; then
    cat "$log"
    exit 1
fi

awk '
    function comma(n, out) {
        out = n
        while (out ~ /^[0-9]+[0-9]{3}$/)
            sub(/[0-9]{3}$/, ",&", out)
        return out
    }
    $2 ~ /^LUT[1-6](_2)?$/ { lut += $1 }
    $2 ~ /^FD/             { ff += $1 }
    $2 ~ /^RAMB/           { bram += $1 }
    $2 ~ /^DSP/            { dsp += $1 }
    END {
        print "synthesis results (yosys XC7)"
        printf "- %s LUTs\n", comma(lut)
        printf "- %s FFs\n", comma(ff)
        if (bram)
            printf "- %s BRAMs\n", comma(bram)
        else
            print "- no BRAM"
        if (dsp)
            printf "- %s DSPs\n", comma(dsp)
        else
            print "- no DSP"
    }
' "$report"
