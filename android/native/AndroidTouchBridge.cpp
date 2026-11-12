// SPDX-License-Identifier: GPL-3.0-only
#include "AndroidTouchBridge.h"

#include <QCoreApplication>
#include <QEvent>
#include <QMouseEvent>
#include <QTouchEvent>
#include <QWidget>
#include <QDebug>

AndroidTouchBridge::AndroidTouchBridge(QWidget* wizard)
    : QObject(wizard), m_wizard(wizard)
{
}

void AndroidTouchBridge::activate()
{
    if (!m_wizard)
        return;

    // QWidget controls (and especially QAbstractScrollArea viewports) are
    // desktop-mouse oriented. Opt them into real touch events so the bridge
    // can forward presses/releases to the ORIGINAL Qt widgets.
    QList<QWidget*> widgets = m_wizard->findChildren<QWidget*>();
    widgets.prepend(m_wizard);
    for (QWidget* widget : widgets) {
        widget->setAttribute(Qt::WA_AcceptTouchEvents, true);
        widget->installEventFilter(this);
    }
}

bool AndroidTouchBridge::eventFilter(QObject* watched, QEvent* event)
{
    const auto type = event->type();
    if (type != QEvent::TouchBegin && type != QEvent::TouchUpdate
        && type != QEvent::TouchEnd && type != QEvent::TouchCancel)
        return false;

    QWidget* receiver = qobject_cast<QWidget*>(watched);
    if (!receiver || !m_wizard || receiver->window() != m_wizard)
        return false;

    auto* touch = static_cast<QTouchEvent*>(event);
    // The setup wizard uses single-pointer buttons and lists. Leave
    // multi-touch to Qt rather than fabricating two mouse pointers.
    if (touch->points().size() > 1)
        return false;

    if (!touch->points().isEmpty())
        m_lastGlobal = touch->points().constFirst().globalPosition();

    QEvent::Type mouseType = QEvent::None;
    Qt::MouseButtons buttons = Qt::NoButton;
    Qt::MouseButton changedButton = Qt::NoButton;

    if (type == QEvent::TouchBegin) {
        // TouchBegin may be accepted by a parent widget even when the finger
        // is over a child button or the QTreeView viewport. Find the actual
        // widget under the finger; otherwise sending mouse events to the
        // wizard itself never activates "Next" or a language list row.
        QWidget* hit = m_wizard->childAt(
            m_wizard->mapFromGlobal(m_lastGlobal.toPoint()));
        m_pressed = hit ? hit : receiver;
        mouseType = QEvent::MouseButtonPress;
        buttons = Qt::LeftButton;
        changedButton = Qt::LeftButton;
        qInfo() << "PineconeMC Android wizard: touch down at" << m_lastGlobal
                << "widget" << receiver->objectName();
    } else if (type == QEvent::TouchUpdate) {
        if (!m_pressed)
            return false;
        mouseType = QEvent::MouseMove;
        buttons = Qt::LeftButton;
    } else {
        if (!m_pressed)
            return false;
        mouseType = QEvent::MouseButtonRelease;
        changedButton = Qt::LeftButton;
    }

    QWidget* target = m_pressed;
    if (!target)
        return false;
    // A canceled gesture must not trigger the button under the finger.
    const QPointF local = type == QEvent::TouchCancel
        ? QPointF(-1000, -1000)
        : QPointF(target->mapFromGlobal(m_lastGlobal.toPoint()));
    QMouseEvent mouse(mouseType, local, local, m_lastGlobal,
                      changedButton, buttons, Qt::NoModifier,
                      Qt::MouseEventSynthesizedByApplication);
    // Consume the accepted touch so Qt does not also synthesize a click.
    QCoreApplication::sendEvent(target, &mouse);
    if (type == QEvent::TouchEnd || type == QEvent::TouchCancel) {
        qInfo() << "PineconeMC Android wizard: touch released";
        m_pressed.clear();
    }
    event->accept();
    return true;
}
