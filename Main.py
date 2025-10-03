import os
import sys
import zipfile
import json
from datetime import datetime
import getpass
import argparse

class VirtualFileSystem:
    def __init__(self, vfs_path=None):
        self.vfs_path = vfs_path
        self.archive = None
        self.current_dir = '/'
        self.vfs_name = os.path.basename(vfs_path) if vfs_path else "default"

        if vfs_path and os.path.exists(vfs_path):
            self.load_vfs(vfs_path)
        elif vfs_path:
            print(f"Файл VFS '{vfs_path}' не найден")

    def load_vfs(self, vfs_path):
        """Загрузка VFS из ZIP-архива"""
        try:
            self.archive = zipfile.ZipFile(vfs_path, 'r')
            self.vfs_path = vfs_path
            self.vfs_name = os.path.basename(vfs_path)
            print(f"VFS '{self.vfs_name}' успешно загружена")
            
            # Проверяем, что архив не пустой
            if len(self.archive.namelist()) == 0:
                print("Внимание: архив пуст")
                
        except zipfile.BadZipFile:
            print(f"Ошибка: файл '{vfs_path}' не является корректным ZIP-архивом")
            self.archive = None
        except Exception as e:
            print(f"Ошибка загрузки VFS: {e}")
            self.archive = None

    def create_test_vfs(self, vfs_path):
        """Создание тестовой VFS для демонстрации"""
        try:
            with zipfile.ZipFile(vfs_path, 'w') as zf:
                zf.writestr('readme.txt', 'Добро пожаловать в тестовую VFS!\nЭто демонстрационный файл.\nТретья строка для теста tail.')
                zf.writestr('documents/doc1.txt', 'Первый документ\nВторая строка\nТретья строка\nЧетвертая\nПятая')
                zf.writestr('documents/report.md', '# Отчет\n## Раздел 1\nСодержание отчета')
                zf.writestr('scripts/hello.py', '#!/usr/bin/env python\nprint("Hello from VFS!")\n# Это тестовый скрипт')
                zf.writestr('scripts/utils.py', 'def helper():\n    return "help"')
                zf.writestr('data/config.json', '{"app": "test", "version": 1.0, "author": "user"}')
                zf.writestr('images/readme.txt', 'Здесь могли бы быть ваши изображения')
            
            print(f"Создана тестовая VFS: {vfs_path}")
            self.load_vfs(vfs_path)
            return True
        except Exception as e:
            print(f"Ошибка создания тестовой VFS: {e}")
            return False

    def get_vfs_info(self):
        """Информация о VFS для команды vfs-info"""
        if not self.archive:
            return "VFS не загружена"

        try:
            file_stats = os.stat(self.vfs_path)
            # Простая хеш-функция для демонстрации
            vfs_hash = hex(hash(f"{self.vfs_name}{file_stats.st_size}{file_stats.st_mtime}"))[-8:]
            
            # Подсчет файлов и директорий
            all_files = self.archive.namelist()
            file_count = len([f for f in all_files if not f.endswith('/')])
            dir_count = len([d for d in all_files if d.endswith('/')])
            
            return {
                'name': self.vfs_name,
                'path': os.path.abspath(self.vfs_path),
                'hash': vfs_hash.upper(),
                'files_count': file_count,
                'dirs_count': dir_count,
                'total_entries': len(all_files),
                'size': file_stats.st_size,
                'modified': datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            return f"Ошибка получения информации: {e}"

    def list_files(self, directory=None):
        """Список файлов в указанной директории"""
        if not self.archive:
            return None

        target_dir = directory if directory else self.current_dir
        target_dir = target_dir.rstrip('/') + '/'
        
        # Если запрашивается корневая директория
        if target_dir == '//':
            target_dir = '/'

        file_list = []
        dir_set = set()
        
        for name in self.archive.namelist():
            if name.startswith(target_dir) and name != target_dir:
                # Получаем относительный путь
                relative_path = name[len(target_dir):]
                
                # Если это файл в текущей директории
                if '/' not in relative_path:
                    file_list.append(relative_path)
                else:
                    # Это поддиректория - берем первую часть пути
                    first_dir = relative_path.split('/')[0]
                    dir_set.add(first_dir)
        
        # Объединяем файлы и директории
        result = list(dir_set) + file_list
        return sorted(result)

    def change_directory(self, new_dir):
        """Смена текущей директории"""
        if not self.archive:
            print("VFS не загружена")
            return False

        if new_dir == '/':
            self.current_dir = '/'
            return True
        elif new_dir == '..':
            if self.current_dir != '/':
                self.current_dir = os.path.dirname(self.current_dir.rstrip('/')) or '/'
            return True
        elif new_dir.startswith('/'):
            # Абсолютный путь
            test_dir = new_dir.rstrip('/') + '/'
        else:
            # Относительный путь
            test_dir = os.path.join(self.current_dir.rstrip('/'), new_dir).replace('\\', '/') + '/'

        # Проверяем существование директории
        for name in self.archive.namelist():
            if name.startswith(test_dir) or name == test_dir.rstrip('/'):
                self.current_dir = test_dir.rstrip('/') or '/'
                return True

        print(f"Директория '{new_dir}' не найдена")
        return False

    def read_file(self, filename):
        """Чтение содержимого файла"""
        if not self.archive:
            return None

        # Обработка абсолютных и относительных путей
        if filename.startswith('/'):
            full_path = filename.lstrip('/')
        else:
            full_path = os.path.join(self.current_dir.lstrip('/'), filename).replace('\\', '/')

        # Убираем лишние слеши
        full_path = full_path.replace('//', '/')

        if full_path in self.archive.namelist():
            try:
                with self.archive.open(full_path) as f:
                    return f.read().decode('utf-8')
            except UnicodeDecodeError:
                print(f"Файл '{filename}' содержит бинарные данные и не может быть прочитан как текст")
                return None
            except Exception as e:
                print(f"Ошибка чтения файла: {e}")
                return None
        else:
            return None

    def file_exists(self, filename):
        """Проверка существования файла"""
        if not self.archive:
            return False

        if filename.startswith('/'):
            full_path = filename.lstrip('/')
        else:
            full_path = os.path.join(self.current_dir.lstrip('/'), filename).replace('\\', '/')

        return full_path in self.archive.namelist()


class ShellEmulator:
    def __init__(self, vfs_path=None, script_path=None):
        self.vfs = VirtualFileSystem(vfs_path)
        self.script_path = script_path
        self.history = []
        self.start_time = datetime.now()
        self.username = getpass.getuser()

    def get_prompt(self):
        """Формирование приглашения с именем VFS"""
        vfs_name = self.vfs.vfs_name if self.vfs.vfs_name else "no-vfs"
        current_dir = self.vfs.current_dir if self.vfs.current_dir != '/' else '/'
        return f"{vfs_name}:{current_dir}> "

    def execute_script(self, script_path):
        """Выполнение стартового скрипта"""
        if not os.path.exists(script_path):
            print(f"Скрипт '{script_path}' не найден")
            return False

        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            print(f"Выполнение скрипта: {script_path}")
            print("-" * 50)

            for line_num, line in enumerate(lines, 1):
                line = line.strip()

                # Пропуск пустых строк и комментариев
                if not line:
                    print(f"[{line_num}] # пустая строка")
                    continue
                elif line.startswith('#'):
                    print(f"[{line_num}] # {line[1:].strip()}")
                    continue

                # Отображение ввода
                print(f"[{line_num}] {line}")

                # Выполнение команды
                self.execute_command(line)

                print()  # Пустая строка для разделения

            print("-" * 50)
            print("Скрипт выполнен успешно")
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
            elif cmd == 'cat':
                self.cmd_cat(args[1:])
            elif cmd == 'pwd':
                self.cmd_pwd()
            elif cmd == 'help':
                self.cmd_help()
            elif cmd == 'exit' or cmd == 'quit':
                print("Выход из эмулятора...")
                sys.exit(0)
            elif cmd == 'clear' or cmd == 'clr':
                self.cmd_clear()
            else:
                print(f"Команда '{cmd}' не найдена. Введите 'help' для списка команд.")

        except Exception as e:
            print(f"Ошибка выполнения команды: {e}")

    def cmd_ls(self, args):
        """Команда ls"""
        directory = args[0] if args else None
        files = self.vfs.list_files(directory)

        if files is None:
            print("VFS не загружена")
            return

        if not files:
            print("Директория пуста")
            return

        for item in files:
            # Определяем тип (файл или директория)
            full_path = os.path.join(self.vfs.current_dir.rstrip('/'), item).replace('\\', '/')
            if full_path + '/' in self.vfs.archive.namelist() or any(
                name.startswith(full_path + '/') for name in self.vfs.archive.namelist()):
                print(f"\033[94m{item}/\033[0m")  # Синий для директорий
            else:
                # Цвета для разных типов файлов
                if item.endswith(('.py', '.sh', '.bat')):
                    print(f"\033[92m{item}\033[0m")  # Зеленый для скриптов
                elif item.endswith(('.txt', '.md', '.json', '.xml')):
                    print(f"\033[93m{item}\033[0m")  # Желтый для текстовых файлов
                else:
                    print(item)  # Обычный цвет для остальных

    def cmd_cd(self, args):
        """Команда cd"""
        if not args:
            self.vfs.change_directory('/')
        else:
            self.vfs.change_directory(args[0])

    def cmd_whoami(self):
        """Команда whoami - вывод текущего пользователя ОС"""
        print(self.username)

    def cmd_tail(self, args):
        """Команда tail - вывод последних строк файла"""
        if not args:
            print("Использование: tail <filename> [lines]")
            print("Пример: tail readme.txt 5")
            return

        filename = args[0]
        lines_count = 10
        if len(args) > 1:
            try:
                lines_count = int(args[1])
                if lines_count <= 0:
                    print("Количество строк должно быть положительным числом")
                    return
            except ValueError:
                print("Количество строк должно быть числом")
                return

        content = self.vfs.read_file(filename)
        if content is None:
            print(f"Файл '{filename}' не найден или недоступен для чтения")
            return

        all_lines = content.split('\n')
        start_index = max(0, len(all_lines) - lines_count)

        print(f"=== Последние {lines_count} строк файла '{filename}' ===")
        for i, line in enumerate(all_lines[start_index:], start_index + 1):
            print(f"{i:4d}: {line}")

    def cmd_cat(self, args):
        """Команда cat - вывод всего содержимого файла"""
        if not args:
            print("Использование: cat <filename>")
            print("Пример: cat readme.txt")
            return

        filename = args[0]
        content = self.vfs.read_file(filename)
        if content is None:
            print(f"Файл '{filename}' не найден или недоступен для чтения")
            return

        print(f"=== Содержимое файла '{filename}' ===")
        for i, line in enumerate(content.split('\n'), 1):
            print(f"{i:4d}: {line}")

    def cmd_vfs_info(self):
        """Команда vfs-info - информация о загруженной VFS"""
        info = self.vfs.get_vfs_info()
        if isinstance(info, str):
            print(info)
        else:
            print("=== Информация о VFS ===")
            print(f"Имя:          {info['name']}")
            print(f"Путь:         {info['path']}")
            print(f"Хеш:          {info['hash']}")
            print(f"Файлы:        {info['files_count']}")
            print(f"Директории:   {info['dirs_count']}")
            print(f"Всего:        {info['total_entries']}")
            print(f"Размер:       {info['size']} байт")
            print(f"Изменен:      {info['modified']}")

    def cmd_history(self):
        """Команда history - история команд"""
        if not self.history:
            print("История команд пуста")
            return

        print("=== История команд (последние 20) ===")
        start_index = max(0, len(self.history) - 20)
        for i, cmd in enumerate(self.history[start_index:], start_index + 1):
            print(f"{i:3d}: {cmd}")

    def cmd_pwd(self):
        """Команда pwd - текущая директория"""
        print(self.vfs.current_dir)

    def cmd_help(self):
        """Команда help - справка по командам"""
        print("=== Доступные команды ===")
        commands = [
            ("ls [dir]", "Список файлов и директорий"),
            ("cd <dir>", "Смена текущей директории"),
            ("pwd", "Текущая директория"),
            ("cat <file>", "Вывод содержимого файла"),
            ("tail <file> [n]", "Последние n строк файла (по умолчанию 10)"),
            ("whoami", "Текущий пользователь системы"),
            ("vfs-info", "Информация о загруженной VFS"),
            ("history", "История выполненных команд"),
            ("clear/clr", "Очистка экрана"),
            ("help", "Эта справка"),
            ("exit/quit", "Выход из программы")
        ]
        
        for cmd, desc in commands:
            print(f"  {cmd:<20} - {desc}")

    def cmd_clear(self):
        """Очистка экрана"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def run_interactive(self):
        """Интерактивный режим"""
        # Если VFS не загружена, предлагаем создать тестовую
        if not self.vfs.archive:
            response = input("VFS не загружена. Создать тестовую VFS? (y/n): ")
            if response.lower() in ['y', 'yes', 'д', 'да']:
                test_path = "test.vfs"
                if self.vfs.create_test_vfs(test_path):
                    print("Тестовая VFS создана и загружена!")
                else:
                    print("Не удалось создать тестовую VFS")
            print()

        # Выполнение стартового скрипта
        if self.script_path:
            if self.execute_script(self.script_path):
                print("Скрипт выполнен. Переход в интерактивный режим...")
            else:
                print("Ошибка выполнения скрипта. Переход в интерактивный режим...")
            print()

        print("=" * 50)
        print("Эмулятор командной оболочки - Вариант 12")
        print("Для справки введите 'help'")
        print("Для выхода введите 'exit' или 'quit'")
        print("=" * 50)
        print()

        while True:
            try:
                command = input(self.get_prompt()).strip()
                if command:
                    self.execute_command(command)
            except KeyboardInterrupt:
                print("\nДля выхода введите 'exit' или 'quit'")
            except EOFError:
                print("\nВыход...")
                break


def create_example_script():
    """Создание примера стартового скрипта"""
    script_content = """# Пример стартового скрипта для эмулятора VFS
# Этот скрипт выполняется при запуске программы

# Покажем информацию о VFS
vfs-info

# Посмотрим что в корневой директории
ls

# Перейдем в директорию documents
cd documents

# Посмотрим файлы в documents
ls

# Посмотрим содержимое файла
tail doc1.txt 3

# Вернемся в корень
cd /

# Покажем историю команд (будет видна в конце)
"""
    
    script_path = "startup_script.txt"
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    print(f"Создан пример скрипта: {script_path}")
    return script_path


def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='Эмулятор командной оболочки - Вариант 12')
    parser.add_argument('--vfs', help='Путь к файлу VFS (ZIP-архив)')
    parser.add_argument('--script', help='Путь к стартовому скрипту')
    parser.add_argument('--create-example', action='store_true', 
                       help='Создать пример VFS и скрипта')

    args = parser.parse_args()

    # Создание примеров если запрошено
    if args.create_example:
        vfs_path = "example.vfs"
        emulator = ShellEmulator()
        if emulator.vfs.create_test_vfs(vfs_path):
            print("Пример VFS создан!")
        script_path = create_example_script()
        print("Запустите программу с параметрами:")
        print(f"python import_o5.py --vfs {vfs_path} --script {script_path}")
        return

    # Создание эмулятора
    emulator = ShellEmulator(args.vfs, args.script)

    # Запуск
    emulator.run_interactive()


if __name__ == "__main__":
    main()
