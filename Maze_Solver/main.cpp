// main.cpp — Colored ASCII Maze Solver with Algorithm Name in Status Lines
// Fully ASCII‐friendly (uses “x” instead of Unicode × or em dashes)

#ifdef _WIN32
  #include <windows.h>    // On Windows, no ioctl support; skip terminal‐size checks
#else
  #include <sys/ioctl.h>  // For fetching terminal size on Unix
  #include <unistd.h>
#endif

#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <stack>
#include <unordered_set>
#include <algorithm>
#include <numeric>
#include <random>
#include <ctime>
#include <thread>
#include <chrono>

using namespace std;

/* ---------- Disjoint Set (Union‐Find) ---------- */
struct DisjointSet {
    vector<int> parent, sz;
    DisjointSet(int n) {
        parent.resize(n);
        iota(parent.begin(), parent.end(), 0);
        sz.assign(n, 1);
    }
    int findRoot(int x) {
        return parent[x] == x ? x : (parent[x] = findRoot(parent[x]));
    }
    void unite(int a, int b) {
        a = findRoot(a);
        b = findRoot(b);
        if (a == b) return;
        if (sz[a] < sz[b]) swap(a, b);
        parent[b] = a;
        sz[a] += sz[b];
    }
};

/* ---------- Maze Structure & Random Generation ---------- */
struct Maze {
    int mazeW, mazeH;
    vector<vector<bool>> hasRightWall, hasDownWall;

    Maze(int w, int h): mazeW(w), mazeH(h) {
        hasRightWall.assign(mazeW, vector<bool>(mazeH, true));
        hasDownWall.assign(mazeW, vector<bool>(mazeH, true));
    }

    void generateRandom() {
        struct Edge { int x, y, dir; };
        vector<Edge> edges;
        for (int y = 0; y < mazeH; y++) {
            for (int x = 0; x < mazeW; x++) {
                if (x + 1 < mazeW) edges.push_back({x, y, 1});
                if (y + 1 < mazeH) edges.push_back({x, y, 2});
            }
        }
        mt19937 rng((unsigned)time(NULL));
        shuffle(edges.begin(), edges.end(), rng);

        DisjointSet ds(mazeW * mazeH);
        for (auto &e : edges) {
            int a = e.y * mazeW + e.x;
            int b = (e.dir == 1) ? (a + 1) : (a + mazeW);
            if (ds.findRoot(a) != ds.findRoot(b)) {
                if (e.dir == 1)      hasRightWall[e.x][e.y] = false;
                else                 hasDownWall[e.x][e.y]  = false;
                ds.unite(a, b);
            }
        }
    }

    bool canMove(int x, int y, int dir) const {
        if (dir == 0) {
            if (y == 0) return false;
            return !hasDownWall[x][y - 1];
        }
        if (dir == 1) {
            if (x + 1 >= mazeW) return false;
            return !hasRightWall[x][y];
        }
        if (dir == 2) {
            if (y + 1 >= mazeH) return false;
            return !hasDownWall[x][y];
        }
        if (dir == 3) {
            if (x == 0) return false;
            return !hasRightWall[x - 1][y];
        }
        return false;
    }
};

/* ---------- Helper: cellId ↔ (x,y) ---------- */
struct Point { int x, y; };
int cellId(int x, int y, int W) { return y * W + x; }
Point cellPt(int idx, int W) { return { idx % W, idx / W }; }

/* ---------- ANSI Color Codes ---------- */
static const string COLOR_CORNER = "\x1b[95m";
static const string COLOR_HORIZ  = "\x1b[94m";
static const string COLOR_VERT   = "\x1b[94m";
static const string COLOR_VISIT  = "\x1b[97m";
static const string COLOR_FRONT  = "\x1b[33m";
static const string COLOR_CUR    = "\x1b[31m";
static const string COLOR_PATH   = "\x1b[32m";
static const string COLOR_RESET  = "\x1b[0m";

/* ---------- ANSI Helpers (clear screen, move cursor) ---------- */
inline void ansiClear() {
    cout << "\x1b[2J\x1b[H";
}
inline void ansiHome() {
    cout << "\x1b[H";
}

/* ---------- Global: animation delay (milliseconds) ---------- */
int g_delayMs = 150;

/* ---------- ASCII Canvas ---------- */
struct AsciiCanvas {
    int mazeW, mazeH, rows, cols;
    vector<string> baseGrid, drawGrid;

    AsciiCanvas(const Maze &mz) {
        mazeW = mz.mazeW;
        mazeH = mz.mazeH;
        rows = 2 * mazeH + 1;
        cols = 2 * mazeW + 1;
        baseGrid.assign(rows, string(cols, ' '));

        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (r % 2 == 0 && c % 2 == 0)      baseGrid[r][c] = '+';
                else if (r % 2 == 0)               baseGrid[r][c] = '-';
                else if (c % 2 == 0)               baseGrid[r][c] = '|';
            }
        }

        for (int y = 0; y < mazeH; y++) {
            for (int x = 0; x < mazeW; x++) {
                int dr = 2 * y + 1, dc = 2 * x + 1;
                baseGrid[dr][dc] = ' ';
                if (!mz.hasRightWall[x][y]) baseGrid[dr][dc + 1] = ' ';
                if (!mz.hasDownWall[x][y])  baseGrid[dr + 1][dc] = ' ';
            }
        }

        baseGrid[1][0] = ' ';
        baseGrid[2 * mazeH - 1][2 * mazeW] = ' ';
    }

    void resetGrid() {
        drawGrid = baseGrid;
    }
};

/* ---------- Get Terminal Size (rows, cols) ---------- */
pair<int,int> getTerminalSize() {
#ifdef _WIN32
    return make_pair(1000, 1000);
#else
    struct winsize w;
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &w) == 0) {
        return make_pair((int)w.ws_row, (int)w.ws_col);
    } else {
        return make_pair(24, 80);
    }
#endif
}

/* ---------- Draw one frame + status line (with algorithm name) ---------- */
void drawFrame(
    AsciiCanvas &canvas,
    const unordered_set<int> &frontierSet,
    const unordered_set<int> &visitedSet,
    int currentCell,
    const string &statusLineWithAlgo
) {
    while (true) {
        auto sz = getTerminalSize();
        int t_rows = sz.first, t_cols = sz.second;
        int need_rows = canvas.rows + 1;
        int need_cols = canvas.cols;
        if (t_rows >= need_rows && t_cols >= need_cols) break;
        ansiClear();
        cout << "Terminal too small. Please resize to at least "
             << need_cols << "x" << need_rows << ".\n";
        this_thread::sleep_for(chrono::milliseconds(200));
    }

    canvas.resetGrid();

    for (int v : visitedSet) {
        Point p = cellPt(v, canvas.mazeW);
        canvas.drawGrid[2*p.y + 1][2*p.x + 1] = '.';
    }
    for (int v : frontierSet) {
        Point p = cellPt(v, canvas.mazeW);
        canvas.drawGrid[2*p.y + 1][2*p.x + 1] = 'o';
    }
    if (currentCell != -1) {
        Point p = cellPt(currentCell, canvas.mazeW);
        canvas.drawGrid[2*p.y + 1][2*p.x + 1] = '@';
    }

    ansiHome();
    cout << "\x1b[2K" << statusLineWithAlgo << "\n";

    for (int r = 0; r < canvas.rows; r++) {
        for (int c = 0; c < canvas.cols; c++) {
            char ch = canvas.drawGrid[r][c];
            switch (ch) {
                case '+': cout << COLOR_CORNER << ch << COLOR_RESET; break;
                case '-': cout << COLOR_HORIZ  << ch << COLOR_RESET; break;
                case '|': cout << COLOR_VERT   << ch << COLOR_RESET; break;
                case '.': cout << COLOR_VISIT  << ch << COLOR_RESET; break;
                case 'o': cout << COLOR_FRONT  << ch << COLOR_RESET; break;
                case '@': cout << COLOR_CUR    << ch << COLOR_RESET; break;
                case '*': cout << COLOR_PATH   << ch << COLOR_RESET; break;
                default:  cout << ch;
            }
        }
        cout << "\n";
    }

    this_thread::sleep_for(chrono::milliseconds(g_delayMs));
}

/* ---------- Draw final path in green (“*”) ---------- */
void drawFinalPath(
    AsciiCanvas &canvas,
    const vector<int> &parentOf,
    int endCell
) {
    canvas.resetGrid();
    for (int v = endCell; v != -1; v = parentOf[v]) {
        Point p = cellPt(v, canvas.mazeW);
        canvas.drawGrid[2*p.y + 1][2*p.x + 1] = '*';
    }

    while (true) {
        auto sz = getTerminalSize();
        int t_rows = sz.first, t_cols = sz.second;
        if (t_rows >= canvas.rows + 1 && t_cols >= canvas.cols) break;
        ansiClear();
        cout << "Terminal too small. Please resize to at least "
             << canvas.cols << "x" << (canvas.rows + 1) << ".\n";
        this_thread::sleep_for(chrono::milliseconds(200));
    }

    ansiHome();
    cout << "\x1b[2K" << "FINAL (exit found) - displaying path\n";
    for (int r = 0; r < canvas.rows; r++) {
        for (int c = 0; c < canvas.cols; c++) {
            char ch = canvas.drawGrid[r][c];
            switch (ch) {
                case '+': cout << COLOR_CORNER << ch << COLOR_RESET; break;
                case '-': cout << COLOR_HORIZ  << ch << COLOR_RESET; break;
                case '|': cout << COLOR_VERT   << ch << COLOR_RESET; break;
                case '*': cout << COLOR_PATH   << ch << COLOR_RESET; break;
                default:  cout << ch;
            }
        }
        cout << "\n";
    }

    this_thread::sleep_for(chrono::seconds(2));
}

/* ---------- DFS (supports skipping animation) ---------- */
void runDFS(const Maze &mz, bool skipAnimation) {
    int W = mz.mazeW, H = mz.mazeH, N = W * H;
    vector<int> parentOf(N, -1);
    unordered_set<int> visitedSet;
    vector<int> stk;

    if (skipAnimation) {
        stk.push_back(0);
        visitedSet.insert(0);
        while (!stk.empty()) {
            int u = stk.back();
            Point pu = cellPt(u, W);
            if (u == cellId(W-1, H-1, W)) break;

            int nextCell = -1;
            for (int dir = 0; dir < 4; dir++) {
                int nx = pu.x + (dir==1) - (dir==3);
                int ny = pu.y + (dir==2) - (dir==0);
                if (nx<0||nx>=W||ny<0||ny>=H) continue;
                int vid = cellId(nx, ny, W);
                if (mz.canMove(pu.x, pu.y, dir) && !visitedSet.count(vid)) {
                    nextCell = vid;
                    break;
                }
            }
            if (nextCell != -1) {
                parentOf[nextCell] = u;
                stk.push_back(nextCell);
                visitedSet.insert(nextCell);
            } else {
                stk.pop_back();
            }
        }
        AsciiCanvas canvas(mz);
        drawFinalPath(canvas, parentOf, cellId(W-1, H-1, W));
        return;
    }

    AsciiCanvas canvas(mz);
    stk.push_back(0);
    visitedSet.insert(0);

    ansiClear();
    cout << "Please resize terminal to fit entire maze, then press Enter...\n";
    cin.ignore(numeric_limits<streamsize>::max(), '\n');

    ansiClear();
    drawFrame(canvas, {}, visitedSet, -1, "DFS - starting DFS");

    while (!stk.empty()) {
        int u = stk.back();
        Point pu = cellPt(u, W);

        if (u == cellId(W-1, H-1, W)) break;

        int nextCell = -1;
        for (int dir = 0; dir < 4; dir++) {
            int nx = pu.x + (dir==1) - (dir==3);
            int ny = pu.y + (dir==2) - (dir==0);
            if (nx<0||nx>=W||ny<0||ny>=H) continue;
            int vid = cellId(nx, ny, W);
            if (mz.canMove(pu.x, pu.y, dir) && !visitedSet.count(vid)) {
                nextCell = vid;
                break;
            }
        }

        if (nextCell != -1) {
            string st1 = "DFS - expanding cell (" +
                         to_string(pu.x) + "," + to_string(pu.y) + ")";
            drawFrame(canvas, {}, visitedSet, u, st1);

            parentOf[nextCell] = u;
            stk.push_back(nextCell);
            visitedSet.insert(nextCell);

            Point pn = cellPt(nextCell, W);
            string st2 = "DFS - add to frontier (" +
                         to_string(pn.x) + "," + to_string(pn.y) + ")";
            drawFrame(canvas, {nextCell}, visitedSet, u, st2);
        } else {
            stk.pop_back();
            string st3 = "DFS - dead end at (" +
                         to_string(pu.x) + "," + to_string(pu.y) + "), backtracking";
            drawFrame(canvas, {}, visitedSet, u, st3);
        }
    }

    drawFinalPath(canvas, parentOf, cellId(W-1, H-1, W));
}

/* ---------- BFS (supports skipping animation) ---------- */
void runBFS(const Maze &mz, bool skipAnimation) {
    int W = mz.mazeW, H = mz.mazeH, N = W * H;
    vector<int> parentOf(N, -1);
    unordered_set<int> visitedSet;
    queue<int> que;

    if (skipAnimation) {
        que.push(0);
        visitedSet.insert(0);
        while (!que.empty()) {
            int u = que.front(); que.pop();
            if (u == cellId(W-1, H-1, W)) break;
            Point pu = cellPt(u, W);
            for (int dir = 0; dir < 4; dir++) {
                int nx = pu.x + (dir==1) - (dir==3);
                int ny = pu.y + (dir==2) - (dir==0);
                if (nx<0||nx>=W||ny<0||ny>=H) continue;
                int vid = cellId(nx, ny, W);
                if (mz.canMove(pu.x, pu.y, dir) && !visitedSet.count(vid)) {
                    visitedSet.insert(vid);
                    parentOf[vid] = u;
                    que.push(vid);
                }
            }
        }
        AsciiCanvas canvas(mz);
        drawFinalPath(canvas, parentOf, cellId(W-1, H-1, W));
        return;
    }

    AsciiCanvas canvas(mz);
    que.push(0);
    visitedSet.insert(0);

    ansiClear();
    cout << "Please resize terminal to fit entire maze, then press Enter...\n";
    cin.ignore(numeric_limits<streamsize>::max(), '\n');

    ansiClear();
    drawFrame(canvas, {}, visitedSet, -1, "BFS - starting BFS");

    while (!que.empty()) {
        int u = que.front(); que.pop();
        Point pu = cellPt(u, W);
        string st1 = "BFS - expanding cell (" +
                     to_string(pu.x) + "," + to_string(pu.y) + ")";
        drawFrame(canvas, {}, visitedSet, u, st1);

        if (u == cellId(W-1, H-1, W)) break;

        for (int dir = 0; dir < 4; dir++) {
            int nx = pu.x + (dir==1) - (dir==3);
            int ny = pu.y + (dir==2) - (dir==0);
            if (nx<0||nx>=W||ny<0||ny>=H) continue;
            int vid = cellId(nx, ny, W);
            if (mz.canMove(pu.x, pu.y, dir) && !visitedSet.count(vid)) {
                visitedSet.insert(vid);
                parentOf[vid] = u;
                que.push(vid);

                string st2 = "BFS - enqueue (" +
                             to_string(nx) + "," + to_string(ny) + ")";
                drawFrame(canvas, {vid}, visitedSet, u, st2);
            }
        }
    }

    drawFinalPath(canvas, parentOf, cellId(W-1, H-1, W));
}

/* ---------- Dijkstra / A* (supports skipping animation) ---------- */
template<typename Heuristic>
void runPQ(const Maze &mz, Heuristic h, const string &algoName, bool skipAnimation) {
    int W = mz.mazeW, H = mz.mazeH, N = W * H;
    vector<int> dist(N, INT_MAX), parentOf(N, -1);
    unordered_set<int> visitedSet;
    using P = pair<int,int>;
    priority_queue<P, vector<P>, greater<P>> pq;

    dist[0] = 0;
    pq.push({ h(0), 0 });

    if (skipAnimation) {
        visitedSet.insert(0);
        while (!pq.empty()) {
            int u = pq.top().second; pq.pop();
            if (u == cellId(W-1, H-1, W)) break;
            if (!visitedSet.count(u)) visitedSet.insert(u);
            Point pu = cellPt(u, W);
            for (int dir = 0; dir < 4; dir++) {
                int nx = pu.x + (dir==1) - (dir==3);
                int ny = pu.y + (dir==2) - (dir==0);
                if (nx<0||nx>=W||ny<0||ny>=H) continue;
                int vid = cellId(nx, ny, W);
                if (mz.canMove(pu.x, pu.y, dir)) {
                    int alt = dist[u] + 1;
                    if (alt < dist[vid]) {
                        dist[vid] = alt;
                        parentOf[vid] = u;
                        pq.push({ alt + h(vid), vid });
                    }
                }
            }
        }
        AsciiCanvas canvas(mz);
        drawFinalPath(canvas, parentOf, cellId(W-1, H-1, W));
        return;
    }

    AsciiCanvas canvas(mz);
    visitedSet.insert(0);

    ansiClear();
    cout << "Please resize terminal to fit entire maze, then press Enter...\n";
    cin.ignore(numeric_limits<streamsize>::max(), '\n');

    ansiClear();
    drawFrame(canvas, {}, visitedSet, -1, algoName + " - starting " + algoName);

    while (!pq.empty()) {
        vector<int> frontierList;
        auto copyPQ = pq;
        while (!copyPQ.empty()) {
            frontierList.push_back(copyPQ.top().second);
            copyPQ.pop();
        }

        int u = pq.top().second; pq.pop();
        if (!visitedSet.count(u)) visitedSet.insert(u);

        Point pu = cellPt(u, W);
        string st1 = algoName + " - expanding cell (" +
                     to_string(pu.x) + "," + to_string(pu.y) + ")";
        drawFrame(canvas,
                  unordered_set<int>(frontierList.begin(), frontierList.end()),
                  visitedSet, u, st1);

        if (u == cellId(W-1, H-1, W)) break;

        for (int dir = 0; dir < 4; dir++) {
            int nx = pu.x + (dir==1) - (dir==3);
            int ny = pu.y + (dir==2) - (dir==0);
            if (nx<0||nx>=W||ny<0||ny>=H) continue;
            int vid = cellId(nx, ny, W);
            if (mz.canMove(pu.x, pu.y, dir)) {
                int alt = dist[u] + 1;
                if (alt < dist[vid]) {
                    dist[vid] = alt;
                    parentOf[vid] = u;
                    pq.push({ alt + h(vid), vid });
                    string st2 = algoName + " - relax edge to (" +
                                 to_string(nx) + "," + to_string(ny) + ")";
                    drawFrame(canvas,
                              unordered_set<int>(frontierList.begin(),
                                                 frontierList.end()),
                              visitedSet, u, st2);
                }
            }
        }
    }

    drawFinalPath(canvas, parentOf, cellId(W-1, H-1, W));
}

/* ---------- Print Legend ---------- */
void printLegend() {
    ansiClear();
    cout << "Legend:\n";
    cout << COLOR_CORNER << "+ " << COLOR_RESET << ": corner of wall\n";
    cout << COLOR_HORIZ  << "- " << COLOR_RESET << ": horizontal wall\n";
    cout << COLOR_VERT   << "| " << COLOR_RESET << ": vertical wall\n";
    cout << COLOR_VISIT  << ". " << COLOR_RESET << ": visited cell (white)\n";
    cout << COLOR_FRONT  << "o " << COLOR_RESET << ": frontier (yellow)\n";
    cout << COLOR_CUR    << "@ " << COLOR_RESET << ": current cell (red)\n";
    cout << COLOR_PATH   << "* " << COLOR_RESET << ": final path (green)\n";
    cout << "\nPress Enter to continue...\n";
    cin.ignore(numeric_limits<streamsize>::max(), '\n');
}

/* ---------- Prompt for speed (faster top speed) ---------- */
void promptSpeed() {
    int s;
    while (true) {
        ansiClear();
        cout << "Choose speed (1=slow ... 10=fast): ";
        if (!(cin >> s)) {
            cin.clear();
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            continue;
        }
        if (s >= 1 && s <= 10) break;
    }
    cin.ignore(numeric_limits<streamsize>::max(), '\n');

    switch (s) {
        case 1:  g_delayMs = 500; break;
        case 2:  g_delayMs = 300; break;
        case 3:  g_delayMs = 200; break;
        case 4:  g_delayMs = 100; break;
        case 5:  g_delayMs = 80;  break;
        case 6:  g_delayMs = 60;  break;
        case 7:  g_delayMs = 40;  break;
        case 8:  g_delayMs = 25;  break;
        case 9:  g_delayMs = 10;  break;
        case 10: g_delayMs = 1;   break;  // Top speed → 1 ms delay
        default: g_delayMs = 150; break;
    }
}

/* ---------- Main Program ---------- */
int main() {
    // Hide the cursor (ANSI code)
    cout << "\x1b[?25l";

    int mazeWidth = 30, mazeHeight = 15;

    while (true) {
        // ── Generate a new maze ──
        Maze mazeObj(mazeWidth, mazeHeight);
        mazeObj.generateRandom();

        // Show the empty maze immediately after generation
        {
            AsciiCanvas canvas(mazeObj);
            // Ensure terminal is large enough
            while (true) {
                auto sz = getTerminalSize();
                int t_rows = sz.first, t_cols = sz.second;
                int need_rows = canvas.rows + 1;
                int need_cols = canvas.cols;
                if (t_rows >= need_rows && t_cols >= need_cols) break;
                ansiClear();
                cout << "Terminal too small. Please resize to at least "
                     << need_cols << "x" << need_rows << ".\n";
                this_thread::sleep_for(chrono::milliseconds(200));
            }
            // Draw empty maze (no visits, no frontier, no current)
            ansiClear();
            // Status line for empty maze
            cout << "EMPTY MAZE - use terminal commands to continue\n";
            for (int r = 0; r < canvas.rows; r++) {
                for (int c = 0; c < canvas.cols; c++) {
                    char ch = canvas.baseGrid[r][c];
                    switch (ch) {
                        case '+': cout << COLOR_CORNER << ch << COLOR_RESET; break;
                        case '-': cout << COLOR_HORIZ  << ch << COLOR_RESET; break;
                        case '|': cout << COLOR_VERT   << ch << COLOR_RESET; break;
                        default:  cout << ch;
                    }
                }
                cout << "\n";
            }
            cout << "\nPress Enter to continue...\n";
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
        }

        // Loop: allow running different algorithms on the same maze
        while (true) {
            ansiClear();
            cout << "Maze " << mazeWidth << "x" << mazeHeight << " generated\n"
                 << "1) DFS   2) BFS   3) Dijkstra   4) A*\n"
                 << "q) Quit\n> ";
            char choice;
            cin >> choice;
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            if (choice == 'q' || choice == 'Q') {
                // Show cursor again before exiting
                cout << "\x1b[?25h";
                return 0;
            }

            // Print legend
            printLegend();

            // ── ASK WHETHER TO SKIP ANIMATION ──
            ansiClear();
            cout << "Press 's' (then Enter) to skip animation, or just press Enter to set speed: ";
            bool skipAnim = false;
            string tmp;
            getline(cin, tmp);
            if (!tmp.empty() && (tmp[0] == 's' || tmp[0] == 'S')) {
                skipAnim = true;
            }

            // If not skipping, ask for speed
            if (!skipAnim) {
                promptSpeed();
            }

            // Run the chosen algorithm
            if (choice == '1') {
                runDFS(mazeObj, skipAnim);
            }
            else if (choice == '2') {
                runBFS(mazeObj, skipAnim);
            }
            else if (choice == '3') {
                auto zeroH = [](int){ return 0; };
                runPQ(mazeObj, zeroH, "Dijkstra", skipAnim);
            }
            else if (choice == '4') {
                auto manH = [&](int v) {
                    Point p = cellPt(v, mazeWidth);
                    return abs(p.x - (mazeWidth - 1)) + abs(p.y - (mazeHeight - 1));
                };
                runPQ(mazeObj, manH, "A*", skipAnim);
            }
            else {
                // Invalid input → back to algorithm menu
                continue;
            }

            // After the algorithm finishes, final path is shown for 2 seconds
            // Now prompt the user to press Enter to proceed (keeps the final path visible)
            cout << "\nPress Enter to continue...";
            cin.ignore(numeric_limits<streamsize>::max(), '\n');

            // ── Next‐step menu: same maze, new maze, or quit ──
            while (true) {
                ansiClear();
                cout << "Choose next step:\n"
                     << "1) Run another algorithm on SAME maze\n"
                     << "2) Generate a NEW maze\n"
                     << "q) Quit\n> ";
                char nextChoice;
                cin >> nextChoice;
                cin.ignore(numeric_limits<streamsize>::max(), '\n');
                if (nextChoice == '1') {
                    break;
                }
                else if (nextChoice == '2') {
                    goto REGENERATE_MAZE;
                }
                else if (nextChoice == 'q' || nextChoice == 'Q') {
                    cout << "\x1b[?25h";
                    return 0;
                }
                else {
                    continue;
                }
            }
        }

        REGENERATE_MAZE:
        continue;
    }

    return 0;
}
