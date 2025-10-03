import os
import sys
import zipfile
import json
from datetime import datetime

class VirtualFileSystem:
    def __init__(self, vfs_path=None):
        self.vfs_path = vfs_path
        self.archive = None
        self.current_dir = '/'
        self.vfs_name = os.path.basename(vfs_path) if vfs_path else "default"

        if vfs_path and os.path.exists(vfs_path):
            self.load_vfs(vfs_path)

    def load_vfs(self, vfs_path):
        """Загрузка VFS из ZIP-архива"""
        try:
            self.archive = zipfile.ZipFile(vfs_path, 'r')
            self.vfs_path = vfs_path
            self.vfs_name = os.path.basename(vfs_path)
            print(f"VFS '{self.vfs_name}' успешно загружена")
        except Exception as e:
            print(f"Ошибка загрузки VFS: {e}")
            self.archive = None

    def get_vfs_info(self):
        """Информация о VFS для команды vfs-info"""
        if not self.archive:
            return "VFS не загружена"

        # Простая хеш-функция (в реальности используйте hashlib.sha256)
        file_stats = os.stat(self.vfs_path)
        vfs_hash = hex(hash(f"{self.vfs_name}{file_stats.st_size}"))[-8:]

        return {
            'name': self.vfs_name,
            'hash': vfs_hash,
            'files_count': len(self.archive.namelist()),
            'size': file_stats.st_size
        }

    def list_files(self, directory=None):
        """Список файлов в указанной директории"""
        if not self.archive:
            print("VFS не загружена")
            return []

        target_dir = directory if directory else self.current_dir
        target_dir = target_dir.rstrip('/') + '/'

        file_list = []
        for name in self.archive.namelist():
            if name.startswith(target_dir) and name != target_dir:
                # Получаем относительный путь
                relative_path = name[len(target_dir):]
                # Если файл находится непосредственно в целевой директории
                if '/' not in relative_path or relative_path.endswith('/'):
                    file_list.append(relative_path.rstrip('/'))

        return sorted(file_list)

    def change_directory(self, new_dir):
        """Смена текущей директории"""
        if not self.archive:
            print("VFS не загружена")
            return

        if new_dir == '/':
            self.current_dir = '/'
        elif new_dir == '..':
            if self.current_dir != '/':
                self.current_dir = os.path.dirname(self.current_dir.rstrip('/')) or '/'
        elif new_dir.startswith('/'):
            # Абсолютный путь
            self.current_dir = new_dir
        else:
            # Относительный путь
            new_path = os.path.join(self.current_dir.rstrip('/'), new_dir).replace('\\', '/')
            # Проверяем существование директории
            dir_check = new_path + '/'
            for name in self.archive.namelist():
                if name.startswith(dir_check):
                    self.current_dir = new_path
                    return
            print(f"Директория '{new_dir}' не найдена")

    def read_file(self, filename):
        """Чтение содержимого файла"""
        if not self.archive:
            return None

        full_path = os.path.join(self.current_dir.rstrip('/'), filename).replace('\\', '/')
        if full_path in self.archive.namelist():
            try:
                with self.archive.open(full_path) as f:
                    return f.read().decode('utf-8')
            except:
                return None
        return None


class ShellEmulator:
    def __init__(self, vfs_path=None, script_path=None):
        self.vfs = VirtualFileSystem(vfs_path)
        self.script_path = script_path
        self.history = []
        self.start_time = datetime.now()

    def get_prompt(self):
        """Формирование приглашения с именем VFS"""
        vfs_name = self.vfs.vfs_name if self.vfs.vfs_name else "no-vfs"
        return f"{vfs_name}:{self.vfs.current_dir}> "

    def execute_script(self, script_path):
        """Выполнение стартового скрипта"""
        if not os.path.exists(script_path):
            print(f"Скрипт '{script_path}' не найден")
            return False

        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            print(f"Выполнение скрипта: {script_path}")

            for line_num, line in enumerate(lines, 1):
                line = line.strip()

                # Пропуск пустых строк и комментариев
                if not line or line.startswith('#'):
                    print(f"[{line_num}] # {line[1:] if line.startswith('#') else 'пустая строка'}")
                    continue

                # Отображение ввода
                print(f"[{line_num}] {line}")

                # Выполнение команды
                self.execute_command(line)

                print()  # Пустая строка для разделения

            return True

        except Exception as e:
            print(f"Ошибка выполнения скрипта: {e}")
            return False

    def execute_command(self, command):
        """Выполнение одной команды"""
        command = command.strip()
        if not command:
            return

        # Добавление в историю
        self.history.append(command)

        args = command.split()
        cmd = args[0].lower()

        try:
            if cmd == 'ls':
                self.cmd_ls(args[1:])
            elif cmd == 'cd':
                self.cmd_cd(args[1:])
            elif cmd == 'whoami':
                self.cmd_whoami()
            elif cmd == 'tail':
                self.cmd_tail(args[1:])
            elif cmd == 'vfs-info':
                self.cmd_vfs_info()
            elif cmd == 'history':
                self.cmd_history()
            elif cmd == 'exit' or cmd == 'quit':
                sys.exit(0)
            elif cmd == 'clear' or cmd == 'clr':
                self.cmd_clear()
            else:
                print(f"Команда '{cmd}' не найдена")

        except Exception as e:
            print(f"Ошибка выполнения команды: {e}")

    def cmd_ls(self, args):
        """Команда ls"""
        directory = args[0] if args else None
        files = self.vfs.list_files(directory)

        if files is None:
            print("Директория не найдена")
            return

        for file in files:
            # Простая эмуляция определения типа файла
            if any(file.endswith(ext) for ext in ['.txt', '.py', '.md']):
                print(file)  # Обычный файл
            else:
                print(file + "/")  # Директория

    def cmd_cd(self, args):
        """Команда cd"""
        if not args:
            self.vfs.change_directory('/')
        else:
            self.vfs.change_directory(args[0])

    def cmd_whoami(self):
        """Команда whoami - вывод текущего пользователя ОС"""
        import getpass
        print(getpass.getuser())

    def cmd_tail(self, args):
        """Команда tail - вывод последних строк файла"""
        if not args:
            print("Usage: tail <filename> [lines]")
            return

        filename = args[0]
        lines_count = 10
        if len(args) > 1:
            try:
                lines_count = int(args[1])
            except ValueError:
                print("Количество строк должно быть числом")
                return

        content = self.vfs.read_file(filename)
        if content is None:
            print(f"Файл '{filename}' не найден или недоступен для чтения")
            return

        all_lines = content.split('\n')
        start_index = max(0, len(all_lines) - lines_count)

        for line in all_lines[start_index:]:
            print(line)

    def cmd_vfs_info(self):
        """Команда vfs-info - информация о загруженной VFS"""
        info = self.vfs.get_vfs_info()
        if isinstance(info, str):
            print(info)
        else:
            print(f"Имя VFS: {info['name']}")
            print(f"Хеш: {info['hash']}")
            print(f"Количество файлов: {info['files_count']}")
            print(f"Размер: {info['size']} байт")

    def cmd_history(self):
        """Команда history - история команд"""
        for i, cmd in enumerate(self.history[-10:], 1):  # Последние 10 команд
            print(f"{i:2d}  {cmd}")

    def cmd_clear(self):
        """Очистка экрана"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def run_interactive(self):
        """Интерактивный режим"""
        if self.script_path:
            self.execute_script(self.script_path)
            print("Скрипт выполнен. Переход в интерактивный режим...")
            print()

        print("Эмулятор командной оболочки (Вариант 12)")
        print("Для выхода введите 'exit' или 'quit'")
        print()

        while True:
            try:
                command = input(self.get_prompt())
                self.execute_command(command)
            except KeyboardInterrupt:
                print("\nДля выхода введите 'exit'")
            except EOFError:
                print("\nВыход...")
                break


def main():
    """Основная функция"""
    import argparse

    parser = argparse.ArgumentParser(description='Эмулятор командной оболочки - Вариант 12')
    parser.add_argument('--vfs', help='Путь к файлу VFS (ZIP-архив)')
    parser.add_argument('--script', help='Путь к стартовому скрипту')

    args = parser.parse_args()

    # Создание эмулятора
    emulator = ShellEmulator(args.vfs, args.script)

    # Запуск
    emulator.run_interactive()


if __name__ == "__main__":
    main()
