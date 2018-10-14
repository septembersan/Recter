import copy
from enum import Enum
import inspect
import logging
import re
import sys
import neovim
__logger__ = logging.getLogger('draw_rect.vim')


class NvimOutLogHandler(logging.Handler):
    """
    python logging handler to output messages to the neovim user.
    """

    _nvim = None
    _terminator = '\n'

    def __init__(self, nvim, *args, **kwargs):
        """Initialize."""
        super().__init__(*args, **kwargs)
        self._nvim = nvim

    def emit(self, record):
        """emit."""
        self._nvim.out_write(self.format(record))
        self._nvim.out_write(self._terminator)
        self.flush()


@neovim.plugin
class TestPlugin2(object):
    """
    Recter.
    """

    def __init__(self, nvim):
        """Recter."""
        self.nvim = nvim
        # update the __logger__ to use neovim for messages
        nvimhandler = NvimOutLogHandler(nvim)
        # nvimhandler.setLevel(logging.INFO)
        nvimhandler.setLevel(logging.DEBUG)
        __logger__.setLevel(logging.DEBUG)
        __logger__.addHandler(nvimhandler)

    @neovim.command("Recter", range='', nargs='*', sync=True)
    def recter(self, args, range):
        """Recter command handler."""
        self.nvim.command(
            "echo('Recter `init mode`: s:srround, i:relabel, "
            "f:focus, m:move rect, y:yank rect, d:delete rect, u:undo')")
        # __logger__.info('start ' + inspect.currentframe().f_code.co_name)
        char = self.nvim.call("nr2char", self.nvim.call("getchar"))
        self.change_mode(char)
        return

    def change_mode(self, mode):
        if mode == 's':
            self.srround()
        elif mode == 'i':
            self.relabel()
        elif mode == 'f':
            self.focus()
        elif mode == 'y':
            self.yank()
        elif mode == 'm':
            self.move()
        elif mode == 'd':
            self.delete()
        elif mode == 'u':
            self.nvim.command("u")
        else:
            return

    # @neovim.autocmd('BufReadPost', pattern='*.py', sync=True)
    # def on_bufenter(self, buffname=None):
    #     __logger__.info('start ' + inspect.currentframe().f_code.co_name)
    #     self.nvim.current.line = "autocmd_handler_insertLeave"

    # @neovim.autocmd('InsertLeave', pattern='*.py', sync=True)
    # def autocmd_handler_insertLeave(self):
    #     __logger__.info('start ' + inspect.currentframe().f_code.co_name)
    #     None

    @neovim.command("RecterCorrectFormat", range='', nargs='*', sync=True)
    def autocmd_handler_insertLeave(self, args, range):
        self.nvim.command("augroup RecterCorrectFormatLoad")
        self.nvim.command("autocmd!")
        self.nvim.command("augroup END")
        __logger__.info('start ' + inspect.currentframe().f_code.co_name)
        vim_buffer = self.copy_vim_buffer()
        curpos = self.nvim.call("getcurpos")
        buf = Buffer.init(vim_buffer)
    
        # check that current cursor position is in rect
        rects = buf.find_no_right_end_rects()
        if not rects:
            __logger__.info('[I] :does not exist no right end rect'
                            + inspect.currentframe().f_code.co_name)
            return
    
        # reshape rects 
        for rect in rects:
            buf.reshape_rect(rect)
    
        self.redraw(buf, curpos)
        self.nvim.command("Recter")
        

    def get_cursor_point(self):
        curpos = self.nvim.call("getcurpos")
        return Buffer.translate_vim_buffer_to_buffer(Point(curpos[1], curpos[2]))

    def relabel(self):
        """
        +-------+
        ||
        +-------+
        """
        # get current vim-buffer
        vim_buffer = self.copy_vim_buffer()
        buf = Buffer.init(vim_buffer)

        # get cursor position
        curpos_point = self.get_cursor_point()

        # check that current cursor position is in rect
        rect = buf.get_rect_on_cursor(curpos_point)
        label_start_pos = None
        if rect is not None:
            # delete string in rect
            rect.delete_label()
            buf.set_rect(rect)
            # move cusor
            vim_point = Buffer.translate_buffer_to_vim_buffer(
                rect.get_label_start_point())
            label_start_pos = Buffer.translate_point_to_curpos(
                self.nvim.call("getcurpos"), vim_point)
            # into instert mode
            self.redraw(buf, label_start_pos)
            self.nvim.command("startinsert")
            self.nvim.command("augroup RecterCorrectFormatLoad")
            self.nvim.command("autocmd!")
            self.nvim.command("autocmd InsertLeave * RecterCorrectFormat")
            self.nvim.command("augroup END")

    def copy_vim_buffer(self):
        vim_buffer = self.nvim.current.buffer
        return [list(line) for line in vim_buffer]

    def redraw(self, buf, curpos):
        self.nvim.command("%delete")
        vim_buffer = []
        for line in buf.buf_table:
            vim_buffer.append("".join(line))
        self.nvim.call("append", 1, vim_buffer)
        self.nvim.command("1delete")
        # self.nvim.current.buffer = vim_buffer
        self.nvim.call('setpos', '.', curpos)
        self.nvim.command("redraw")

    def delete(self):
        # get current vim-buffer
        vim_buffer = self.copy_vim_buffer()
        curpos = self.nvim.call("getcurpos")
        buf = Buffer.init(vim_buffer)

        # get cursor position
        curpos_point = self.get_cursor_point()

        rect = buf.get_rect_on_cursor(curpos_point)
        if rect is None:
            self.nvim.command(
                "echo('Recter navi: Retry delete operation on `target rect`')")
            return

        buf.delete_rect(rect)
        self.redraw(buf, curpos)

    def echo(self, value):
        self.nvim.command("echo(\"{}\")".format(value))

    def focus(self):
        # get current vim-buffer
        vim_buffer = self.copy_vim_buffer()
        curpos = self.nvim.call("getcurpos")
        buf = Buffer.init(vim_buffer)

        # get cursor position
        curpos_point = self.get_cursor_point()

        rect = buf.get_rect_on_cursor(curpos_point)
        if rect is None:
            rect = buf.find_rect_nearest_neighbor(curpos_point)
            if rect is None:
                self.nvim.command(
                    "echo('Recter navi: does not exist to focus rect')")
                return
            vim_point = Buffer.translate_buffer_to_vim_buffer(rect.edges['UL'])
            curpos = Buffer.translate_point_to_curpos(curpos, vim_point)
            self.redraw(buf, curpos)

        cursorline_org_status = self.nvim.current.window.options['cursorline']
        cursorcolumn_org_status = self.nvim.current.window.options['cursorcolumn']
        self.nvim.command("set cursorline")
        self.nvim.command("set cursorcolumn")

        self.nvim.command("echo('Recter `focus mode`: s:srround, i:relabel, "
        "f:focus, m:move rect, y:yank rect, d:delete rect, u:undo')")

        # focus
        while True:
            char = self.nvim.call("nr2char", self.nvim.call("getchar"))
            target_rects = []
            if char == 'h':
                target_rects = [
                    rect for rect in buf.find_rects() if rect.edges['UL'].x < curpos_point.x]
            elif char == 'j':
                target_rects = [
                    rect for rect in buf.find_rects() if rect.edges['UL'].y > curpos_point.y]
            elif char == 'k':
                target_rects = [
                    rect for rect in buf.find_rects() if rect.edges['UL'].y < curpos_point.y]
            elif char == 'l':
                target_rects = [
                    rect for rect in buf.find_rects() if rect.edges['UL'].x > curpos_point.x]
            else:
                self.change_mode(char)
                self.nvim.current.window.options['cursorline'] = cursorline_org_status
                self.nvim.current.window.options['cursorcolumn'] = cursorcolumn_org_status
                return

            if not target_rects:
                continue
            sorted_rects = sorted(
                target_rects, key=lambda rect: Points.calc_point_distance(
                    curpos_point, rect.edges['UL']))
            curpos_point = sorted_rects[0].edges['UL']
            # update cursor point
            vim_point = Buffer.translate_buffer_to_vim_buffer(curpos_point)
            curpos = Buffer.translate_point_to_curpos(curpos, vim_point)
            self.redraw(buf, curpos)
            # self.highlight_rect(sorted_rects[0])

    def highlight_rect(self, rect):
        vlen = rect.edges['LL'].y - rect.edges['UL'].y
        hlen = rect.edges['UR'].x - rect.edges['UL'].x
        self.nvim.command("exe \"normal!\<C-v>{}j{}l\"".format(vlen, hlen))

    def yank(self):
        # get current vim-buffer
        vim_buffer = self.copy_vim_buffer()
        curpos = self.nvim.call("getcurpos")
        buf = Buffer.init(vim_buffer)

        # get cursor position
        curpos_point = self.get_cursor_point()

        rect = buf.get_rect_on_cursor(curpos_point)
        if rect is None:
            self.nvim.command(
                "echo('Recter navi: Retry yank operation on `target rect`')")
            return

        cursorline_org_status = self.nvim.current.window.options['cursorline']
        cursorcolumn_org_status = self.nvim.current.window.options['cursorcolumn']
        self.nvim.command("set cursorline")
        self.nvim.command("set cursorcolumn")

        self.nvim.command("echo('Recter `yank mode`: s:srround, i:relabel, "
        "f:focus, m:move rect, y:yank rect, d:delete rect, u:undo')")

        # past
        h_space_dist = 1
        v_space_dist = 0
        while True:
            char = self.nvim.call("nr2char", self.nvim.call("getchar"))
            if char == 'h':
                distance = rect.get_len_horizon_line() + h_space_dist
                rect.jump_move(Direction.L, distance)
            elif char == 'j':
                distance = rect.get_len_vertical_line() + v_space_dist
                rect.jump_move(Direction.D, distance)
            elif char == 'k':
                distance = rect.get_len_vertical_line() + v_space_dist
                rect.jump_move(Direction.U, distance)
            elif char == 'l':
                distance = rect.get_len_horizon_line() + h_space_dist
                rect.jump_move(Direction.R, distance)
            else:
                self.change_mode(char)
                self.nvim.current.window.options['cursorline'] = cursorline_org_status
                self.nvim.current.window.options['cursorcolumn'] = cursorcolumn_org_status
                return

            vim_point = Buffer.translate_buffer_to_vim_buffer(
                rect.get_label_start_point())
            curpos = Buffer.translate_point_to_curpos(
                self.nvim.call("getcurpos"), vim_point)
            buf.set_rect(rect)
            self.redraw(buf, curpos)

    def move(self):
        # get current vim-buffer
        vim_buffer = self.copy_vim_buffer()
        curpos = self.nvim.call("getcurpos")
        buf = Buffer.init(vim_buffer)

        # get cursor position
        curpos_point = self.get_cursor_point()

        rect = buf.get_rect_on_cursor(curpos_point)
        if rect is None:
            self.nvim.command("echo('Recter navi: Retry move operation on `target rect`')")
            return

        self.nvim.command("echo('Recter `move mode`: s:srround, i:relabel, "
        "f:focus, m:move rect, y:yank rect, d:delete rect, u:undo')")

        # move loop
        buf.delete_rect(rect)
        buf_back = copy.deepcopy(buf)
        while True:
            char = self.nvim.call("nr2char", self.nvim.call("getchar"))
            if char == 'h':
                rect.move(Direction.L)
                curpos[2] -= 1
            elif char == 'j':
                rect.move(Direction.D)
                curpos[1] += 1
            elif char == 'k':
                rect.move(Direction.U)
                curpos[1] -= 1
            elif char == 'l':
                rect.move(Direction.R)
                curpos[2] += 1
            else:
                self.change_mode(char)
                return

            buf = copy.deepcopy(buf_back)
            buf.set_rect(rect)
            self.redraw(buf, curpos)

    def srround(self):
        # get current vim-buffer
        vim_buffer = self.copy_vim_buffer()
        buf = Buffer.init(vim_buffer)

        # get cursor position
        curpos = self.nvim.call("getcurpos")
        curpos_point = Buffer.translate_vim_buffer_to_buffer(
            Point(curpos[1], curpos[4]))
        current_line = self.nvim.current.line

        # get cursor_word
        cursor_word = " "
        if len(current_line) < curpos[4]:
            return
        if current_line[curpos_point.x] == " ":
            return
        if current_line[curpos_point.x] != " ":
            cursor_word = self.nvim.call("expand", "<cWORD>")

        # detect rects current buffer
        # get start point of cursor position word
        cursor_word_start_point = Point
        cursor_word_end_point = Point
        match_iter = re.finditer(re.escape(cursor_word), current_line)
        for match in match_iter:
            if curpos_point.x >= match.start() and curpos_point.x <= match.end():
                cursor_word_start_point = Point(curpos_point.y, match.start())
                cursor_word_end_point = Point(curpos_point.y, match.end() - 1)
                # self.nvim.call("setline", '.', "match!!!")
                break

        buf.create_rect(cursor_word_start_point, cursor_word_end_point)
        self.redraw(buf, curpos)
        self.nvim.command("Recter")

class Direction(Enum):
    L = 1
    D = 2
    U = 3
    R = 4

class Points(object):
    def __init__(self, points):
        self.points = points

    @classmethod
    def generate_range_point(cls, start_point, end_point):
        if end_point.y < start_point.y or end_point.x < start_point.x:
            raise Exception

        range_points = []
        # horizon
        if start_point.y == end_point.y:
            for x in range(start_point.x, end_point.x + 1):
                range_points.append(Point(start_point.y, x))
        # vertical
        else:
            for y in range(start_point.y, end_point.y + 1):
                range_points.append(Point(y, start_point.x))


        return range_points

    @classmethod
    def calc_point_distance(cls, point1, point2):
        return ((point1.y - point2.y) ** 2) + ((point1.x - point2.x) ** 2)

class Point(object):
    def __init__(self, y, x):
        self.y = y
        self.x = x

    def _format(self):
        return 'y:{}, x:{}'.format(self.y, self.x)

    def __repr__(self):
        return '<{} at {} {}>'.format(
            type(self).__name__, hex(id(self)), self._format())

    def __eq__(self, other):
        if self.y == other.y and self.x == other.x:
            return True
        return False

    def __add__(self, other):
        return Point(self.y + other.y, self.x + other.x)

    def is_only_y_equal(self, other):
        if self.y == other.y and self.x != other.x:
            return True
        return False

    def is_only_x_equal(self, other):
        if self.y != other.y and self.x == other.x:
            return True
        return False


class Rect(object):
    edge_shape = "+"
    horizon_line_shape = "-"
    vertical_line_shape = "|"

    def __init__(self, upper_left, upper_right, lower_right, lower_left,
                 rect_in_lines=[]):
        self.edges = {'UL': upper_left, 'UR': upper_right,
                     'LR': lower_right, 'LL': lower_left}

        if len(rect_in_lines) == 0:
            # label is empty
            self.label = []
            self.label_points = {'START': upper_left+Point(1, 1), 'END': upper_right+Point(1, 1)}
        else:
            self.label_points = {'START': upper_left+Point(1, 1), 'END': upper_right+Point(1, -1)}
            self.label = rect_in_lines[0]

    def delete_label(self):
        self.label = []
        self.label_points = {'START': self.edges['UL'] + Point(1, 1), 'END': self.edges['UR'] + Point(1, 1)}

    def get_label_start_point(self):
        return self.label_points['START']

    def jump_move(self, direction, distance):
        [self.move(direction) for i in range(distance)]

    def move(self, direction):
        if direction == Direction.L:
            if self.edges['UL'].x == 0:
                return
            for point in self.edges.values():
                point.x -= 1
            for lp in self.label_points.values():
                lp.x -= 1
        if direction == Direction.D:
            for point in self.edges.values():
                point.y += 1
            for lp in self.label_points.values():
                lp.y += 1
        if direction == Direction.U:
            if self.edges['UL'].y == 0:
                return
            for point in self.edges.values():
                point.y -= 1
            for lp in self.label_points.values():
                lp.y -= 1
        if direction == Direction.R:
            for point in self.edges.values():
                point.x += 1
            for lp in self.label_points.values():
                lp.x += 1

    def get_len_horizon_line(self):
        return self.edges['UR'].x - self.edges['UL'].x + 1

    def get_len_vertical_line(self):
        return self.edges['LL'].y - self.edges['UL'].y + 1

    @classmethod
    def init(cls, upper_left, lower_right):
        upper_right = Point(upper_left.y, lower_right.x)
        lower_left = Point(lower_right.y, upper_left.x)
        cls.edges = {'UL': upper_left, 'UR': upper_right,
                     'LR': lower_right, 'LL': lower_left}
        return cls

class Buffer(object):
    def __init__(self, buf_table, rects=[], no_right_end_rects=[]):
        self.buf_table = buf_table
        self.no_right_end_rects = no_right_end_rects

    @classmethod
    def init(cls, buf_table):
        return Buffer(buf_table)

    @classmethod
    def translate_vim_buffer_to_buffer(self, point):
        return Point(point.y - 1, point.x - 1)

    @classmethod
    def translate_buffer_to_vim_buffer(self, point):
        return Point(point.y + 1, point.x + 1)

    @classmethod
    def translate_point_to_curpos(self, curpos, point):
        curpos[1] = point.y
        curpos[2] = point.x
        curpos[4] = point.x
        return curpos

    def delete_rect(self, rect):
        upper_limit_y = rect.edges['UL'].y
        lower_limit_y = rect.edges['LL'].y + 1
        lines = []
        for y in range(upper_limit_y, lower_limit_y):
            lines.append(self.buf_table[y])

        left_end_x = rect.edges['UL'].x
        right_end_x = rect.edges['UR'].x + 1
        for line in lines:
            line[left_end_x:right_end_x] = [' '] * len(line[left_end_x:right_end_x])

    def find_rect_nearest_neighbor(self, point):
        rects = self.find_rects()
        if not rects:
            return None

        distance = sys.maxsize
        nearest_neighbor_rect = None
        for rect in rects:
            rect_point = rect.edges['UL']
            t_distance = Points.calc_point_distance(point, rect_point)
            if t_distance < distance:
                distance = t_distance
                nearest_neighbor_rect = copy.deepcopy(rect)

        return nearest_neighbor_rect

    def get_rect_on_cursor(self, point):
        rects = self.find_rects()
        if not rects:
            return None

        for rect in rects:
            if rect.edges['UL'].y <= point.y and rect.edges['LL'].y >= point.y:
                if rect.edges['UL'].x <= point.x and rect.edges['UR'].x >= point.x:
                    return rect
        return None

    def relabel(self, char, rect):
        self.buf_table[rect.edges['UL'].y + 1][rect.edges['UL'].x + 1] = char

    def padding(self, point):
        if self.is_accesible_point(point):
            return
        if point.y >= len(self.buf_table):
            number_of_adding_line = point.y - (len(self.buf_table) - 1)
            for i in range(number_of_adding_line):
                self.buf_table.append([])
        line = self.buf_table[point.y]
        padding_len = (point.x + 1) - len(line)
        for i in range(padding_len):
            line.insert(len(line), " ")

    def get_char_with_point(self, point):
        return self.buf_table[point.y][point.x]

    def set_char_with_point(self, set_char, point):
        if not self.is_accesible_point(point):
            self.padding(point)
        self.buf_table[point.y][point.x] = set_char

    def set_rect(self, rect):
        if rect.edges['UL'].y < 0 or rect.edges['UL'].x < 0:
            return

        # draw line
        points = []
        points.extend(Points.generate_range_point(rect.edges['UL'], rect.edges['UR']))
        points.extend(Points.generate_range_point(rect.edges['LL'], rect.edges['LR']))
        [self.set_char_with_point(Rect.horizon_line_shape, p) for p in points]

        points = []
        points.extend(Points.generate_range_point(rect.edges['UR'], rect.edges['LR']))
        points.extend(Points.generate_range_point(rect.edges['UL'], rect.edges['LL']))
        [self.set_char_with_point(Rect.vertical_line_shape, p) for p in points]

        # draw edges
        for edge_point in rect.edges.values():
            self.set_char_with_point(Rect.edge_shape, edge_point)

        # draw label
        if len(rect.label) == 0:
            # pack `|   |` -> `||`
            label_line = self.buf_table[rect.label_points['START'].y]
            del label_line[rect.label_points['START'].x:rect.label_points['END'].x-1]
            return
        points = Points.generate_range_point(rect.label_points['START'], rect.label_points['END'])
        for i, p in enumerate(points):
            self.set_char_with_point(rect.label[i], p)

    def is_accesible_point(self, point):
        try:
            self.buf_table[point.y][point.x]
        except(Exception):
            return False
        return True

    def reshape_rect(self, rect):
        start_point = rect.get_label_start_point()
        end_point = None
        # nothing to do
        if not self.is_accesible_point(start_point):
            __logger__.info('[I] not accesible point ' + inspect.currentframe().f_code.co_name)
            return

        cline = self.buf_table[start_point.y]
        line = cline[start_point.x:]
        for i, s in enumerate(line):
            if s == Rect.vertical_line_shape:
                end_point = Point(start_point.y, start_point.x + i)
                break
        if end_point is None:
            __logger__.info('[I] does not exsit vertical_line_shape ' 
                            + inspect.currentframe().f_code.co_name)
            return

        # case edge_shape pos eqall vertical_line_shape pos
        diffx_of_edge_and_vline = abs(end_point.x - rect.edges['UR'].x)
        if end_point.x == rect.edges['UR'].x:
            return

        # in
        if end_point.x < rect.edges['UR'].x:
            for i in range(diffx_of_edge_and_vline):
                del self.buf_table[start_point.y - 1][start_point.x]
                del self.buf_table[start_point.y + 1][start_point.x]
            return

        # out
        if end_point.x > rect.edges['UR'].x:
            for i in range(diffx_of_edge_and_vline):
                self.buf_table[start_point.y - 1].insert(start_point.x, Rect.horizon_line_shape)
                self.buf_table[start_point.y + 1].insert(start_point.x, Rect.horizon_line_shape)
            return


    def find_no_right_end_rects(self):
        no_right_end_rects = []

        edge_points = self.find_edge_points()
        if not edge_points:
            __logger__.info('[I] :does not find edges!!'
                            + inspect.currentframe().f_code.co_name)
            return None
        for point in edge_points:
            upper_right_point = self.find_upper_right_point(point)
            if upper_right_point is None:
                continue
            lower_right_point = self.find_lower_right_point_no_vline(upper_right_point)
            if lower_right_point is None:
                continue
            lower_left_point = self.find_lower_left_point(lower_right_point)
            if lower_left_point is None:
                continue
            
            no_right_end_rects.append(
                Rect(point, upper_right_point, lower_right_point, lower_left_point))
        return no_right_end_rects


    def find_rects(self):
        rects = []

        edge_points = self.find_edge_points()
        if not edge_points:
            return rects

        for upper_left_point in edge_points:
            upper_right_point = self.find_upper_right_point(upper_left_point)
            if upper_right_point is None:
                continue
            lower_right_point = self.find_lower_right_point(upper_right_point)
            if lower_right_point is None:
                continue
            lower_left_point = self.find_lower_left_point(lower_right_point)
            if lower_left_point is None:
                continue

            rect_in_lines = [line[upper_left_point.x+1:upper_right_point.x] for line in self.buf_table[upper_left_point.y+1:lower_left_point.y]]
            rects.append(
                Rect(upper_left_point, upper_right_point, lower_right_point, lower_left_point, rect_in_lines))

        return rects

    def find_edge_points(self):
        edge_points = []
        for y, line in enumerate(self.buf_table):
            for x, s in enumerate(line):
                if s == Rect.edge_shape:
                    edge_points.append(Point(y, x))
        return edge_points

    def find_upper_right_point(self, point):
        line = self.buf_table[point.y]
        exit_hline = False
        if not self.is_accesible_point(point):
            return None
        # ignore "+----+"
        #         ^
        start_point = point.x + 1
        for x, s in enumerate(line[start_point:]):
            if s != Rect.horizon_line_shape and s != Rect.edge_shape:
                return None
            if s == Rect.horizon_line_shape:
                exit_hline = True
                continue
            if s == Rect.edge_shape:
                if not exit_hline:
                    return None
                point = Point(point.y, x + start_point)
                return point
        return None

    def find_lower_right_point(self, point):
        start_point = point.y + 1
        exit_vline = False
        for y, line in enumerate(self.buf_table[start_point:]):
            if not self.is_accesible_point(Point(start_point + y, point.x)):
                return None

            s = line[point.x]
            if s != Rect.vertical_line_shape and s != Rect.edge_shape:
                return None
            if s == Rect.vertical_line_shape:
                exit_vline = True
                continue
            if s == Rect.edge_shape:
                if not exit_vline:
                    return None
                point = Point(y + start_point, point.x)
                return point
        return None

    def find_lower_right_point_no_vline(self, point):
        start_point = point.y + 1
        for y, line in enumerate(self.buf_table[start_point:]):
            if not self.is_accesible_point(Point(start_point + y, point.x)):
                continue

            s = line[point.x]
            if s != Rect.vertical_line_shape and s != Rect.edge_shape:
                continue
            if s == Rect.vertical_line_shape:
                return None
            if s == Rect.edge_shape:
                point = Point(y + start_point, point.x)
                return point
        return None

    def find_lower_left_point(self, point):
        line = self.buf_table[point.y]
        start_point = point.x - 1
        rev_line = line[start_point::-1]
        exit_hline = False
        for x, s in enumerate(rev_line):
            if s != Rect.horizon_line_shape and s != Rect.edge_shape:
                return None
            if s == Rect.horizon_line_shape:
                exit_hline = True
                continue
            if s == Rect.edge_shape:
                if not exit_hline:
                    return None
                point = Point(point.y, start_point-x)
                return point
        return None
        None

    def is_rects_overlaping(self, rect1, rect2):
        # contain
        for edge in rect2.edges:
            if rect1.edges['UL'].y <= edge.y and rect1.edges['LR'].y >= edge.y:
                # if rect1.edges['UL'].x <= edge.x and edges.x >= rect1.edges['LR'].x:
                return True
        return False

    def is_in_range(self, point):
        if point.y < 1 or point.y >= len(self.buf_table) - 1:
            return False
        if point.x < 1 or point.x > len(self.buf_table[point.y]) - 1:
            return False
        return True

    def create_rect(self, start_point, end_point):
        # on text?
        if not self.is_in_range(start_point):
            return
        if not self.is_in_range(end_point):
            return
        upper_left = Point(start_point.y - 1, start_point.x - 1)
        lower_right = Point(end_point.y + 1, end_point.x + 1)
        rect = Rect.init(upper_left, lower_right)
        self.padding(rect.edges['UR'])
        self.padding(rect.edges['LR'])
        # for rt in self.rects:
        #     if self.is_rects_overlaping(rect, rt):
        #         print("overlaping")
        self.print_rect(rect)


    def print_rect(self, rect):
        for count, edge in enumerate(rect.edges.values()):
            self.buf_table[edge.y][edge.x] = Rect.edge_shape

        self.print_vs_line(rect.edges['UL'], rect.edges['UR'])
        self.print_hs_line(rect.edges['UR'], rect.edges['LR'])
        self.print_vs_line(rect.edges['LL'], rect.edges['LR'])
        self.print_hs_line(rect.edges['UL'], rect.edges['LL'])


    def print_vs_line(self, left_point, right_point):
        line = self.buf_table[left_point.y]
        strs = [Rect.horizon_line_shape] * ((right_point.x - left_point.x) - 1)
        line[left_point.x+1:right_point.x] = strs


    def print_hs_line(self, upper_point, lower_point):
        lines = self.buf_table[upper_point.y+1:lower_point.y]
        for line in lines:
            try:
                line[upper_point.x] = Rect.vertical_line_shape
            except(Exception):
                line.insert(len(line), " ")
                line[upper_point.x] = Rect.vertical_line_shape

    def display(self):
        for line in self.buf_table:
            for s in line:
                print(s, end="")
            print("")
