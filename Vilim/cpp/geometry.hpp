#pragma once

#include "utils.hpp"

using F = double;
using std::array;

template<typename T>
void a () {
    int b = 2;
}

struct point
{
    F x = 0;
    F y = 0;

    F tan() { return y / x; };
    F r() { return std::sqrt(x * x + y * y); }

    point normal() { return *this / r(); }

    friend point operator+(point a, point b) { return {a.x + b.x, a.y + b.y}; }
    friend point operator-(point a, point b) { return {a.x - b.x, a.y - b.y}; }

    template <typename S>
    friend point operator/(point p, S s) { return {p.x / s, p.y / s}; }

    template <typename S>
    friend point operator*(point p, S s) { return {p.x * s, p.y * s}; }

    friend F operator*(point a, point b) { return a.x * b.x + a.y * b.y; }
};

using vector = point;

struct edge
{
    point a;
    point b;
    // Custom Edge Iterator
};

struct polygon
{
    const static int N = 3;

    template <typename T>
    using array = array<T, N>;

    array<point> vertex;

    inline point center() { return avg(vertex); }
};

struct line
{
    point p;
    F rate;

    static point instrsection(line l1, line l2)
    {
        return point();
    }

    inline static line between(point a, point b) { return {avg(a, b), -1 / (b - a).tan()}; }
    inline static line between(edge e) { return between(e.a, e.b); }

    inline static line connecting(point a, point b) { return {a, (b - a).tan()}; }
    inline static line connecting(edge e) { return connecting(e.a, e.b); }
};
