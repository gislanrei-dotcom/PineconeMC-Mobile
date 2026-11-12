// SPDX-License-Identifier: GPL-3.0-only
#pragma once

#include <QObject>
#include <QPointF>
#include <QPointer>

class QEvent;
class QWidget;

// Android-only adapter for the original PineconeMC setup wizard (Qt Widgets).
// Only handles touch events for which this class explicitly opts in; it does
// not change game input or synthesize duplicate events from mouse events.
class AndroidTouchBridge final : public QObject {
public:
    explicit AndroidTouchBridge(QWidget* wizard);
    void activate();

protected:
    bool eventFilter(QObject* watched, QEvent* event) override;

private:
    QPointer<QWidget> m_wizard;
    QPointer<QWidget> m_pressed;
    QPointF m_lastGlobal;
};
