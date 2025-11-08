import 'dart:async';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import '../../service/background_notification_service.dart';
import '../web_message_handler/tp_web_message_handler.dart';

/// 處理來自 WebView 的 watch 訊息（啟動背景監控）
class WatchMessageHandler extends TPWebMessageHandler {
  static Timer? _periodicTimer;

  @override
  String get name => 'watch';

  @override
  Future<void> handle({
    required Object? message,
    required WebUri? sourceOrigin,
    required bool isMainFrame,
    required Function(WebMessage replyWebMessage)? onReply,
  }) async {
    print('[WatchMessageHandler] Received watch message');
    try {
      // 啟動背景檢查標記
      await BackgroundNotificationService.startPeriodicCheck();
      
      // 測試用：立即執行一次
      await BackgroundNotificationService.executeImmediately();
      
      // 啟動 5 分鐘週期檢查（App 存活時）
      _startPeriodicCheck();
      
      print('[WatchMessageHandler] Background notification service started');
      onReply?.call(replyWebMessage(data: true));
    } catch (e) {
      print('[WatchMessageHandler] Error: $e');
      onReply?.call(replyWebMessage(data: false));
    }
  }

  static void _startPeriodicCheck() {
    // 取消舊的計時器
    _periodicTimer?.cancel();
    
    // 每 5 分鐘執行一次檢查（當 App 在前景時）
    _periodicTimer = Timer.periodic(const Duration(minutes: 5), (timer) async {
      print('[WatchMessageHandler] Periodic check triggered');
      await BackgroundNotificationService.executeImmediately();
    });
  }

  static void stopPeriodicCheck() {
    _periodicTimer?.cancel();
    _periodicTimer = null;
  }
}

/// 處理來自 WebView 的 unwatch 訊息（停止背景監控）
class UnwatchMessageHandler extends TPWebMessageHandler {
  @override
  String get name => 'unwatch';

  @override
  Future<void> handle({
    required Object? message,
    required WebUri? sourceOrigin,
    required bool isMainFrame,
    required Function(WebMessage replyWebMessage)? onReply,
  }) async {
    print('[UnwatchMessageHandler] Received unwatch message');
    try {
      // 停止背景檢查標記
      await BackgroundNotificationService.stopPeriodicCheck();
      
      // 停止週期計時器
      WatchMessageHandler.stopPeriodicCheck();
      
      print('[UnwatchMessageHandler] Background notification service stopped');
      onReply?.call(replyWebMessage(data: true));
    } catch (e) {
      print('[UnwatchMessageHandler] Error: $e');
      onReply?.call(replyWebMessage(data: false));
    }
  }
}
