import 'dart:async';
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'notification_service.dart';

/// 背景通知服務（使用 Android AlarmManager 實現週期檢查）
/// 注意：由於 Flutter 限制，真正的背景任務需要在 Android 原生層實作
/// 這裡提供基本的檢查邏輯，供前景或原生層呼叫
class BackgroundNotificationService {
  /// 初始化服務（預留給未來擴展）
  static Future<void> initialize() async {
    // Android AlarmManager 需要在原生層設定
    // 這裡只做 Dart 層的初始化
    print('[BackgroundNotificationService] Initialized');
  }

  /// 啟動週期性檢查（發送訊息給原生層）
  static Future<void> startPeriodicCheck() async {
    print('[BackgroundNotificationService] Start periodic check requested');
    // 實際的週期任務會在原生 Android 層透過 AlarmManager 實作
    // 這裡只做標記，表示使用者想要背景通知
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('background_notification_enabled', true);
  }

  /// 停止週期性檢查
  static Future<void> stopPeriodicCheck() async {
    print('[BackgroundNotificationService] Stop periodic check requested');
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('background_notification_enabled', false);
  }

  /// 立即執行一次檢查（供測試或前景呼叫）
  static Future<void> executeImmediately() async {
    print('[BackgroundNotificationService] Execute check immediately');
    await _checkAndNotify();
  }

  /// 檢查邏輯：讀取收藏與通知設定，發送施工警報
  static Future<void> _checkAndNotify() async {
    print('[BackgroundTask] Starting check...');

    final prefs = await SharedPreferences.getInstance();
    final favoritesJson = prefs.getString('mapFavorites') ?? '[]';
    final notificationsJson = prefs.getString('placeNotifications') ?? '{}';

    List<dynamic> favorites = [];
    Map<String, dynamic> notifications = {};

    try {
      favorites = jsonDecode(favoritesJson);
    } catch (e) {
      print('[BackgroundTask] Failed to decode favorites: $e');
      return;
    }

    try {
      notifications = jsonDecode(notificationsJson);
    } catch (e) {
      print('[BackgroundTask] Failed to decode notifications: $e');
    }

    if (favorites.isEmpty) {
      print('[BackgroundTask] No favorites found');
      return;
    }

    // 檢查每個有啟用通知的收藏
    for (final fav in favorites) {
      final placeId = fav['id'];
      if (placeId == null) continue;

      final enabled = notifications[placeId] == true;
      if (!enabled) continue;

      final recommendations = fav['recommendations'] ?? [];
      if (recommendations is! List) continue;

      // 計算施工地點數量
      int constructionCount = 0;
      for (final rec in recommendations) {
        if (rec is Map<String, dynamic>) {
          final dsid = rec['dsid'];
          final props = rec['props'];
          if (dsid == 'construction' ||
              (props is Map && (props['AP_NAME'] != null || props['PURP'] != null))) {
            constructionCount++;
          }
        }
      }

      if (constructionCount > 0) {
        final placeName = fav['name'] ?? '收藏地點';
        await NotificationService.showNotification(
          title: '$placeName 附近施工資訊',
          content: '此收藏 1 公里內有 $constructionCount 個施工地點',
        );
        print('[BackgroundTask] Notification sent for $placeName (construction: $constructionCount)');
      }
    }

    print('[BackgroundTask] Check completed');
  }
}
