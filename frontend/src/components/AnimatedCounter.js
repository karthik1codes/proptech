import React, { useState, useEffect, useRef } from 'react';

/**
 * AnimatedCounter - A counter that animates from 0 to the target value
 * @param {number} value - Target value to count to
 * @param {function} formatter - Optional formatting function
 * @param {number} duration - Animation duration in ms (default: 1000)
 * @param {string} suffix - Optional suffix to append (e.g., '%')
 * @param {number} decimals - Number of decimal places
 */
export default function AnimatedCounter({ 
  value, 
  formatter, 
  duration = 1000, 
  suffix = '', 
  decimals = 0 
}) {
  const [displayValue, setDisplayValue] = useState(0);
  const previousValueRef = useRef(0);
  const animationRef = useRef(null);

  useEffect(() => {
    const targetValue = typeof value === 'number' ? value : 0;
    const startValue = previousValueRef.current;
    const startTime = performance.now();

    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Easing function (ease-out cubic)
      const easeOut = 1 - Math.pow(1 - progress, 3);
      
      const currentValue = startValue + (targetValue - startValue) * easeOut;
      setDisplayValue(currentValue);

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        previousValueRef.current = targetValue;
      }
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [value, duration]);

  const formattedValue = formatter 
    ? formatter(displayValue) 
    : `${displayValue.toFixed(decimals)}${suffix}`;

  return (
    <span className="animate-count-up">
      {formattedValue}
    </span>
  );
}
