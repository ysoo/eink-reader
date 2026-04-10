from constants import BOOKS_DIR, TODO_PATH

class SyncMixin:

    def _wifi_sync_silent(self):
        """Sync on startup without user feedback if WiFi connects quickly."""
        try:
            self._wifi_sync(silent=True)
        except:
            pass

    def _wifi_sync(self, silent=False):
        import wifi, config, os as _os

        if not silent:
            self.display.show_lines(['', '  Connecting...'], 'SYNC', None)

        if not wifi.connect(config.WIFI_SSID, config.WIFI_PASSWORD):
            if not silent:
                self.display.show_lines(['', '  WiFi failed.'], 'SYNC', None)
                import utime; utime.sleep_ms(1500)
            return

        try:
            _step = 'get queue'
            queue = wifi.get_json(config.SERVER_URL + '/api/queue')

            for item in (queue if isinstance(queue, list) else []):
                try:
                    if item['type'] == 'book':
                        dest = BOOKS_DIR + '/' + item['name']
                        if not silent:
                            self.display.show_lines(
                                ['', '  ' + item['name'][:43]], 'SYNC', None)
                        wifi.download_to_file(item['url'], dest)
                    elif item['type'] == 'todo':
                        wifi.download_to_file(item['url'], '/sd/todo_incoming.txt')
                except Exception:
                    pass  # Skip failed items; ack still clears the queue

            # Upload todo if it exists (merge on server is idempotent)
            try:
                _os.stat(TODO_PATH)
            except OSError:
                pass  # no todo file yet, skip
            else:
                _step = 'post todo'
                wifi.post_file(config.SERVER_URL + '/api/todo/sync', TODO_PATH)

            _step = 'ack'
            wifi.get_json(config.SERVER_URL + '/api/queue/ack')

        except Exception as e:
            raise Exception(_step + ': ' + str(e))
        finally:
            wifi.disconnect()   # always free the ~50 KB, even on error

        # Merge incoming todo after WiFi is off (no RAM pressure)
        try:
            _os.stat('/sd/todo_incoming.txt')
            import todo
            todo.merge_incoming('/sd/todo_incoming.txt', TODO_PATH)
            _os.remove('/sd/todo_incoming.txt')
        except:
            pass

        self.books = self._list_books()
        self._clamp_menu()
        if not silent:
            self.draw_menu(full=True)
