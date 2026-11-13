// SPDX-License-Identifier: GPL-3.0-only
// Android touch support for the *existing* Qt Widgets launcher.
// One touch handler for all scroll areas, including lazily created dialogs.
// In particular, avoid QScroller / incremental QWidget scroll blitting:
// some Qt Android devices display stale or displaced text after those blits.
#include "AndroidTouchScrolling.h"
#include <QAbstractItemView>
#include <QAbstractScrollArea>
#include <QApplication>
#include <QCoreApplication>
#include <QEvent>
#include <QMouseEvent>
#include <QPointer>
#include <QScrollBar>
#include <QTouchEvent>
#include <QTreeView>
#include <QWidget>
#include <QDebug>
#include <cmath>

namespace {
class MobileTouchFilter final : public QObject {
public:
    explicit MobileTouchFilter(QObject* application) : QObject(application)
    {
        application->installEventFilter(this);
        for (auto* widget : QApplication::allWidgets())
            if (auto* area = qobject_cast<QAbstractScrollArea*>(widget))
                prepare(area);
    }

protected:
    bool eventFilter(QObject* watched, QEvent* event) override
    {
        switch (event->type()) {
        case QEvent::Polish:
        case QEvent::Show:
            if (auto* area = qobject_cast<QAbstractScrollArea*>(watched))
                prepare(area);
            return false;
        case QEvent::TouchBegin:
        case QEvent::TouchUpdate:
        case QEvent::TouchEnd:
        case QEvent::TouchCancel:
            return handleTouch(qobject_cast<QWidget*>(watched),
                               static_cast<QTouchEvent*>(event));
        default:
            return false;
        }
    }

private:
    QPointer<QAbstractScrollArea> m_scroll;
    QPointer<QWidget> m_touchTarget;
    QPointF m_lastGlobal;
    QPointF m_firstGlobal;
    qreal m_remY = 0, m_remX = 0;
    bool m_drag = false;

    static void prepare(QAbstractScrollArea* area)
    {
        if (!area || area->property("_pineconeScrollReady").toBool())
            return;
        area->setProperty("_pineconeScrollReady", true);
        if (auto* viewport = area->viewport()) {
            viewport->setAttribute(Qt::WA_AcceptTouchEvents, true);
            // Backing store MUST fully redraw every region on Android.
            viewport->setAttribute(Qt::WA_StaticContents, false);
            viewport->setAttribute(Qt::WA_OpaquePaintEvent, false);
            viewport->setAutoFillBackground(true);
        }
        if (auto* view = qobject_cast<QAbstractItemView*>(area)) {
            view->setVerticalScrollMode(QAbstractItemView::ScrollPerPixel);
            view->setHorizontalScrollMode(QAbstractItemView::ScrollPerPixel);
            view->setSelectionBehavior(QAbstractItemView::SelectRows);
            if (auto* tree = qobject_cast<QTreeView*>(area)) {
                tree->setUniformRowHeights(true);
                tree->setWordWrap(false);
            }
        }
    }

    static bool isInsideViewport(QWidget* target, QAbstractScrollArea* area)
    {
        auto* viewport = area->viewport();
        return viewport && (viewport == target || viewport->isAncestorOf(target));
    }

    static QAbstractScrollArea* closestScrollable(QWidget* target)
    {
        for (QWidget* node = target; node; node = node->parentWidget()) {
            auto* area = qobject_cast<QAbstractScrollArea*>(node);
            if (!area || !isInsideViewport(target, area))
                continue;
            prepare(area);
            if (area->verticalScrollBar()->maximum() > area->verticalScrollBar()->minimum()
                || area->horizontalScrollBar()->maximum() > area->horizontalScrollBar()->minimum())
                return area;
        }
        return nullptr;
    }

    static int pixelDelta(qreal distance, qreal& remainder)
    {
        remainder += distance;
        const auto whole = static_cast<int>(std::trunc(remainder));
        remainder -= whole;
        return whole;
    }

    static void sendTap(QWidget* receiver, QPointF global)
    {
        if (!receiver)
            return;
        const QPointF local(receiver->mapFromGlobal(global.toPoint()));
        QMouseEvent down(QEvent::MouseButtonPress, local, local, global,
                         Qt::LeftButton, Qt::LeftButton, Qt::NoModifier,
                         Qt::MouseEventSynthesizedByApplication);
        QCoreApplication::sendEvent(receiver, &down);
        QMouseEvent up(QEvent::MouseButtonRelease, local, local, global,
                       Qt::LeftButton, Qt::NoButton, Qt::NoModifier,
                       Qt::MouseEventSynthesizedByApplication);
        QCoreApplication::sendEvent(receiver, &up);
    }

    static void repaintAll(QAbstractScrollArea* area)
    {
        if (!area)
            return;
        // Invalidating just the list viewport was insufficient: stale text
        // remained in siblings and even overlapping dialogs. Force a complete
        // top-level backing-store repaint after changing the scroll position.
        if (auto* top = area->window())
            top->repaint(top->rect());
        else if (auto* viewport = area->viewport())
            viewport->repaint(viewport->rect());
    }

    bool handleTouch(QWidget* receiver, QTouchEvent* event)
    {
        if (!receiver)
            return false;
        const auto type = event->type();
        const auto& points = event->points();
        if (type == QEvent::TouchBegin) {
            if (points.size() != 1)
                return false;
            // QScrollArea forms have interactive children. Detect the
            // scrollable ancestor of either the viewport or a child control.
            auto* area = closestScrollable(receiver);
            if (!area)
                return false;
            m_scroll = area;
            m_touchTarget = receiver;
            m_firstGlobal = m_lastGlobal = points.constFirst().globalPosition();
            m_remY = m_remX = 0;
            m_drag = false;
            event->accept();
            return true;
        }
        if (!m_scroll || !m_touchTarget)
            return false;
        // QTouchEvent can be delivered to an ancestor after the first event.
        if (receiver != m_touchTarget && receiver != m_scroll->viewport())
            return false;
        const QPointF global = points.isEmpty() ? m_lastGlobal
                                                 : points.constFirst().globalPosition();
        if (type == QEvent::TouchUpdate) {
            if ((global - m_firstGlobal).manhattanLength() > 12)
                m_drag = true;
            if (m_drag) {
                const QPointF delta = global - m_lastGlobal;
                auto* sy = m_scroll->verticalScrollBar();
                auto* sx = m_scroll->horizontalScrollBar();
                if (sy && sy->maximum() > sy->minimum())
                    sy->setValue(sy->value() - pixelDelta(delta.y(), m_remY));
                if (sx && sx->maximum() > sx->minimum()
                    && std::abs(delta.x()) > std::abs(delta.y()) * 1.5)
                    sx->setValue(sx->value() - pixelDelta(delta.x(), m_remX));
                repaintAll(m_scroll);
            }
            m_lastGlobal = global;
            event->accept();
            return true;
        }
        if (type == QEvent::TouchEnd || type == QEvent::TouchCancel) {
            const bool tap = !m_drag && type == QEvent::TouchEnd;
            auto target = m_touchTarget;
            auto scroll = m_scroll;
            m_scroll.clear();
            m_touchTarget.clear();
            // Do not send a fake click after a drag; route an ordinary tap to
            // the ORIGINAL child widget or the original item-view viewport.
            if (tap && target) {
                if (qobject_cast<QAbstractItemView*>(scroll.data()))
                    target = scroll->viewport();
                sendTap(target, global);
            } else {
                repaintAll(scroll);
            }
            event->accept();
            return true;
        }
        return false;
    }
};
}

void AndroidTouchScrolling::install(QObject* application)
{
    if (application)
        new MobileTouchFilter(application);
}
