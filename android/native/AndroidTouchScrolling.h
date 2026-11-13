// SPDX-License-Identifier: GPL-3.0-only
#pragma once
class QObject;
namespace AndroidTouchScrolling {
// Enable single-finger kinetic scrolling for all Qt item views and scroll
// areas, including dialogs that appear after the launcher starts.
void install(QObject* application);
}
