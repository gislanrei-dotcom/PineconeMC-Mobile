// SPDX-License-Identifier: GPL-3.0-only
#include "AndroidTouchScrolling.h"

#include <QAbstractItemView>
#include <QAbstractScrollArea>
#include <QApplication>
#include <QEvent>
#include <QScroller>
#include <QScrollBar>
#include <QWidget>
#include <QDebug>

namespace {
class MobileScrollingInstaller final : public QObject {
public:
    explicit MobileScrollingInstaller(QObject* application) : QObject(application)
    {
        // QApplication event filters observe top-level windows, nested
        // dialogs and lazy-created version/mod lists without reparenting
        // anything or replacing the upstream Qt selection models.
        application->installEventFilter(this);
        for (QWidget* widget : QApplication::allWidgets()) {
            if (auto* area = qobject_cast<QAbstractScrollArea*>(widget))
                enableScrolling(area);
        }
    }

protected:
    bool eventFilter(QObject* watched, QEvent* event) override
    {
        // A new QAbstractScrollArea receives Show after its viewport exists.
        // This also covers combo-box drop-downs and mod loader dialogs.
        if (event->type() == QEvent::Show ||
            event->type() == QEvent::Polish) {
            if (auto* area = qobject_cast<QAbstractScrollArea*>(watched))
                enableScrolling(area);
        }
        return false;
    }

private:
    static void enableScrolling(QAbstractScrollArea* area)
    {
        if (!area || area->property("_pineconeTouchScrolling").toBool())
            return;
        QWidget* viewport = area->viewport();
        if (!viewport)
            return;
        area->setProperty("_pineconeTouchScrolling", true);
        // Qt's native QScroller differentiates short taps (item selection)
        // from finger drags (kinetic scrolling); do not convert finger moves
        // into fake mouse clicks, which shifts the selected list row.
        viewport->setAttribute(Qt::WA_AcceptTouchEvents, true);
        QScroller::grabGesture(viewport, QScroller::TouchGesture);
        if (auto* view = qobject_cast<QAbstractItemView*>(area)) {
            view->setVerticalScrollMode(QAbstractItemView::ScrollPerPixel);
            view->setHorizontalScrollMode(QAbstractItemView::ScrollPerPixel);
        }
        qInfo() << "PineconeMC Android: finger scroll attached" << area->metaObject()->className();
    }
};
}

void AndroidTouchScrolling::install(QObject* application)
{
    if (application)
        new MobileScrollingInstaller(application);
}
