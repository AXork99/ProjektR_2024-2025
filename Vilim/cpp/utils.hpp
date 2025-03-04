#pragma once

#include <utility>
#include <array>
#include <cmath> // Prefer <cmath> over <math.h> in C++

template <typename F>
F sum(F f)
{
    return f;
}

template <typename F, typename... REST>
F sum(F f, REST... rest)
{
    return f + sum(rest...); // Properly expand the parameter pack
}

template <typename F, typename... T>
F avg(F f, T... rest)
{
    return sum(f, rest...) / (sizeof...(T) + 1);
}

template <std::size_t N, typename T>
T avg(const std::array<T, N> &arr) // Pass by const reference to avoid unnecessary copies
{
    T total = T{}; // Ensure `total` is initialized
    for (const T &el : arr)
        total = total + el;
    return total / N;
}