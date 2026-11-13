// SPDX-License-Identifier: GPL-3.0-only
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
#include <QWidget>
#include <QDebug>
#include <cmath>

// Do NOT use QScroller::grabGesture on nested QTreeViews: the kinetic scroll
// animation can scroll/paint only part of the viewport on Qt for Android
// (stale version labels overlay dates and other panels). Handle finger-drag
// directly and request complete view repaints instead. Keep the original
// Qt widgets, proxy models and normal QScrollBar positions.
namespace {

class TouchScrollInstaller final : public QObject {
public:
    explicit TouchScrollInstaller(QObject* application) : QObject(application)
    {
        application->installEventFilter(this);
        for (QWidget* widget : QApplication::allWidgets()) {
            if (auto* area = qobject_cast<QAbstractScrollArea*>(widget))
                prepare(area);
        }
    }

protected:
    bool eventFilter(QObject* watched, QEvent* event) override
    {
        switch (event->type()) {
        case QEvent::Show:
        case QEvent::Polish:
            if (auto* area = qobject_cast<QAbstractScrollArea*>(watched))
                prepare(area);
            return false;
        case QEvent::TouchBegin:
        case QEvent::TouchUpdate:
        case QEvent::TouchEnd:
        case QEvent::TouchCancel:
            return touchEvent(watched, static_cast<QTouchEvent*>(event));
        default:
            return false;
        }
    }

private:
    QPointer<QAbstractScrollArea> m_activeArea;
    QPointer<QWidget> m_activeViewport;
    QPointF m_startPos;
    QPointF m_lastPos;
    QPointF m_lastGlobal;
    qreal m_verticalFraction = 0;
    qreal m_horizontalFraction = 0;
    bool m_wasDrag = false;

    static void prepare(QAbstractScrollArea* area)
    {
        if (!area || area->property("_pineconeTouchScrollReady").toBool())
            return;
        QWidget* viewport = area->viewport();
        if (!viewport)
            return;
        area->setProperty("_pineconeTouchScrollReady", true);
        viewport->setAttribute(Qt::WA_AcceptTouchEvents, true);
        if (auto* view = qobject_cast<QAbstractItemView*>(area)) {
            // Paint every row and every column as ONE full viewport instead
            // of relying on partial scroll blits (which left ghost labels).
            view->setViewportUpdateMode(QAbstractItemView::FullViewportUpdate);
            view->setVerticalScrollMode(QAbstractItemView::ScrollPerPixel);
            view->setHorizontalScrollMode(QAbstractItemView::ScrollPerPixel);
            view->setSelectionBehavior(QAbstractItemView::SelectRows);
            if (auto* tree = qobject_cast<QTreeView*>(area))
                tree->setUniformRowHeights(true);
        }
        qInfo() << "PineconeMC Android: stable finger drag enabled for"
                << area->metaObject()->className();
    }

    static int scrollAmount(qreal delta, qreal& fraction)
    {
        fraction += delta;
        const int step = static_cast<int>(std::trunc(fraction));
        fraction -= step;
        return step;
    }

    static void sendClick(QWidget* widget, const QPointF& local,
                          const QPointF& global)
    {
        if (!widget)
            return;
        QMouseEvent press(QEvent::MouseButtonPress, local, local, global,
                          Qt::LeftButton, Qt::LeftButton,
                          Qt::NoModifier,
                          Qt::MouseEventSynthesizedByApplication);
        QCoreApplication::sendEvent(widget, &press);
        QMouseEvent release(QEvent::MouseButtonRelease, local, local, global,
                            Qt::LeftButton, Qt::NoButton,
                            Qt::NoModifier,
                            Qt::MouseEventSynthesizedByApplication);
        QCoreApplication::sendEvent(widget, &release);
    }

    bool touchEvent(QObject* watched, QTouchEvent* touch)
    {
        auto* viewport = qobject_cast<QWidget*>(watched);
        if (!viewport || touch->points().size() != 1)
            return false;

        // QAbstractScrollArea uses a child widget as its viewport.
        auto* area = qobject_cast<QAbstractScrollArea*>(viewport->parentWidget());
        const auto type = touch->type();
        if (type == QEvent::TouchBegin) {
            if (!area || area->viewport() != viewport)
                return false;
            prepare(area);
            m_activeArea = area;
            m_activeViewport = viewport;
            m_startPos = touch->points().first().position();
            m_lastPos = m_startPos;
            m_lastGlobal = touch->points().first().globalPosition();
            m_wasDrag = false;
            m_verticalFraction = 0;
            m_horizontalFraction = 0;
            touch->accept();
            return true;
        }
        if (viewport != m_activeViewport || !m_activeArea)
            return false;
        if (type == QEvent::TouchUpdate) {
            const QPointF pos = touch->points().first().position();
            m_lastGlobal = touch->points().first().globalPosition();
            if ((pos - m_startPos).manhattanLength() > 9)
                m_wasDrag = true;
            if (m_wasDrag) {
                const QPointF delta = pos - m_lastPos;
                QScrollBar* vertical = m_activeArea->verticalScrollBar();
                QScrollBar* horizontal = m_activeArea->horizontalScrollBar();
                if (vertical && vertical->maximum() > vertical->minimum()) {
                    const int dy = scrollAmount(delta.y(), m_verticalFraction);
                    if (dy != 0) vertical->setValue(vertical->value() - dy);
                }
                if (horizontal && horizontal->maximum() > horizontal->minimum()
                    && std::abs(delta.x()) > std::abs(delta.y()) * 1.3) {
                    const int dx = scrollAmount(delta.x(), m_horizontalFraction);
                    if (dx != 0) horizontal->setValue(horizontal->value() - dx);
                }
                // Explicitly invalidate the entire viewport after dragging.
                m_activeViewport->update(m_activeViewport->rect());
            }
            m_lastPos = pos;
            touch->accept();
            return true;
        }
        if (type == QEvent::TouchEnd || type == QEvent::TouchCancel) {
            const bool click = !m_wasDrag && type == QEvent::TouchEnd;
            const QPointF pos = touch->points().first().position();
            const QPointF global = touch->points().first().globalPosition();
            auto widget = m_activeViewport;
            m_activeArea.clear();
            m_activeViewport.clear();
            if (click && widget)
                sendClick(widget, pos, global);
            else if (widget)
                widget->update(widget->rect());
            touch->accept();
            return true;
        }
        return false;
    }
};

} // namespace

void AndroidTouchScrolling::install(QObject* application)
{
    if (application)
        new TouchScrollInstaller(application);
}
