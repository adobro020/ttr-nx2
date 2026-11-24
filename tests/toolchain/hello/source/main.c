// SPDX-License-Identifier: GPL-2.0-only
//
// Phase 0 toolchain proof: the smallest libounce console program. It shows
// that the pinned devkit container produces a loadable NRO. It does nothing
// else and touches no files.
#include <stdio.h>
#include <switch.h>

int main(void)
{
    consoleInit(NULL);
    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);

    printf("TTR NX2 (unofficial) - toolchain hello\n");
    printf("Not affiliated with Nintendo, Disney or the TTR team.\n\n");
    printf("Press + to return to hbmenu.\n");

    while (appletMainLoop()) {
        padUpdate(&pad);
        if (padGetButtonsDown(&pad) & HidNpadButton_Plus)
            break;
        consoleUpdate(NULL);
    }

    consoleExit(NULL);
    return 0;
}
