/**
 * Currency and number formatting utilities for Indian locale
 * All values displayed in Indian Rupees (₹) with Lakhs/Crores formatting
 */

/**
 * Format number to Indian currency (₹)
 * @param {number} value - The value to format
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (value) => {
  if (value === null || value === undefined || isNaN(value)) return '₹0';
  
  const absValue = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  
  // Use Indian number system (Lakhs and Crores)
  if (absValue >= 10000000) {
    // Crores (1 Cr = 10,000,000)
    const crores = absValue / 10000000;
    return `${sign}₹${crores.toFixed(2)} Cr`;
  } else if (absValue >= 100000) {
    // Lakhs (1 L = 100,000)
    const lakhs = absValue / 100000;
    return `${sign}₹${lakhs.toFixed(2)} L`;
  } else {
    // Standard Indian formatting for smaller numbers
    return `${sign}₹${new Intl.NumberFormat('en-IN').format(Math.round(absValue))}`;
  }
};

/**
 * Format to Lakhs specifically
 * @param {number} value - The value to format
 * @returns {string} Formatted string in Lakhs
 */
export const formatLakhs = (value) => {
  if (value === null || value === undefined || isNaN(value)) return '₹0';
  
  const absValue = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  
  if (absValue >= 10000000) {
    const crores = absValue / 10000000;
    return `${sign}₹${crores.toFixed(2)} Cr`;
  } else if (absValue >= 100000) {
    const lakhs = absValue / 100000;
    return `${sign}₹${lakhs.toFixed(2)} L`;
  } else if (absValue >= 1000) {
    const thousands = absValue / 1000;
    return `${sign}₹${thousands.toFixed(1)}K`;
  } else {
    return `${sign}₹${Math.round(absValue)}`;
  }
};

/**
 * Format number with Indian locale
 * @param {number} value - The value to format
 * @param {number} decimals - Number of decimal places (default: 0)
 * @returns {string} Formatted number string
 */
export const formatNumber = (value, decimals = 0) => {
  if (value === null || value === undefined || isNaN(value)) return '0';
  
  if (Math.abs(value) >= 10000000) {
    return `${(value / 10000000).toFixed(2)} Cr`;
  } else if (Math.abs(value) >= 100000) {
    return `${(value / 100000).toFixed(2)} L`;
  }
  
  return new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
};

/**
 * Format percentage
 * @param {number} value - The value to format (0-1 or 0-100)
 * @param {number} decimals - Number of decimal places (default: 1)
 * @returns {string} Formatted percentage string
 */
export const formatPercent = (value, decimals = 1) => {
  if (value === null || value === undefined || isNaN(value)) return '0%';
  
  // If value is between 0 and 1, multiply by 100
  const percentage = value <= 1 && value >= 0 ? value * 100 : value;
  
  return `${percentage.toFixed(decimals)}%`;
};

/**
 * Format large numbers compactly
 * @param {number} value - The value to format
 * @returns {string} Compact formatted string
 */
export const formatCompact = (value) => {
  if (value === null || value === undefined || isNaN(value)) return '0';
  
  const absValue = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  
  if (absValue >= 1000000000) {
    return `${sign}${(absValue / 1000000000).toFixed(1)}B`;
  } else if (absValue >= 1000000) {
    return `${sign}${(absValue / 1000000).toFixed(1)}M`;
  } else if (absValue >= 1000) {
    return `${sign}${(absValue / 1000).toFixed(1)}K`;
  }
  
  return `${sign}${absValue}`;
};

/**
 * Format date for display
 * @param {string|Date} date - The date to format
 * @returns {string} Formatted date string
 */
export const formatDate = (date) => {
  if (!date) return '';
  
  const d = new Date(date);
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(d);
};

/**
 * Format datetime for display
 * @param {string|Date} date - The datetime to format
 * @returns {string} Formatted datetime string
 */
export const formatDateTime = (date) => {
  if (!date) return '';
  
  const d = new Date(date);
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d);
};

/**
 * Calculate percentage change
 * @param {number} current - Current value
 * @param {number} previous - Previous value
 * @returns {object} Object with value and direction
 */
export const calculateChange = (current, previous) => {
  if (!previous || previous === 0) {
    return { value: 0, direction: 'neutral' };
  }
  
  const change = ((current - previous) / previous) * 100;
  return {
    value: Math.abs(change).toFixed(1),
    direction: change > 0 ? 'up' : change < 0 ? 'down' : 'neutral',
  };
};
