<?php


/**
 * The base configuration for WordPress
 *
 * The wp-config.php creation script uses this file during the installation.
 * You don't have to use the website, you can copy this file to "wp-config.php"
 * and fill in the values.
 *
 * This file contains the following configurations:
 *
 * * Database settings
 * * Secret keys
 * * Database table prefix
 * * ABSPATH
 *
 * @link https://developer.wordpress.org/advanced-administration/wordpress/wp-config/
 *
 * @package WordPress
 */

// ** Database settings - You can get this info from your web host ** //
/** The name of the database for WordPress */
define( 'DB_NAME', 'xkhvbgqqku_n89b1' );

/** Database username */
define( 'DB_USER', 'xkhvbgqqku_n89b1' );

/** Database password */
define( 'DB_PASSWORD', 'V.3Scpz2u^(Ef[H&tY]72&&5' );

/** Database hostname */
define( 'DB_HOST', 'localhost' );

/** Database charset to use in creating database tables. */
define( 'DB_CHARSET', 'utf8' );

/** The database collate type. Don't change this if in doubt. */
define( 'DB_COLLATE', '' );

/**#@+
 * Authentication unique keys and salts.
 *
 * Change these to different unique phrases! You can generate these using
 * the {@link https://api.wordpress.org/secret-key/1.1/salt/ WordPress.org secret-key service}.
 *
 * You can change these at any point in time to invalidate all existing cookies.
 * This will force all users to have to log in again.
 *
 * @since 2.6.0
 */
define('AUTH_KEY',         'm0eHhz1VQAtAHc2x7c4aPO3smV66TWFBjZIaEoqVfvOFEcb96FfFQ4rTB9fUj8vn');
define('SECURE_AUTH_KEY',  'ZeBFnDTG9iAw33c666JrNcwSpjgSePMDOMkwVXa2BDT27QQbV6JmYQQAro3bGktp');
define('LOGGED_IN_KEY',    'BkFBtPBMrw1KahSJ0AODiaiZwGRu5C69D6IMHNtoBzCvnEWwBYGS7XBV8LD9dc5d');
define('NONCE_KEY',        'RTo3JrO5dXuu9c1Tv0xXjNkTN7CM2MaUgkhQ6Wss5EENvLOiHsMLHq1arzOKAlJ2');
define('AUTH_SALT',        'LCKY1ewjpOhbDZgmF3R9Hja50UTB6wqYhSQz3fUcbgBV7h22BTFlTVThV2LB0ff3');
define('SECURE_AUTH_SALT', 'dkAvC9MmORysQpLRByFe3SG0wHCKBRZcoiXnV6akHyTOTQ5JeuUvZOxPoMBvTW8I');
define('LOGGED_IN_SALT',   'nkCgDzJL9mHLKNI6HhVHmll7E7Klmjd15enUwJweO6FcQC89fRdi1TfPZmKg6lbp');
define('NONCE_SALT',       '3xFnTd6ggCMgoYpvKUZN894gvaM9Zry44ffMdEZvRMjtPTIxa9ST4DlQ1Bfqx0IS');

/**
 * Other customizations.
 */
define('WP_TEMP_DIR',dirname(__FILE__).'/wp-content/uploads');


/**#@-*/

/**
 * WordPress database table prefix.
 *
 * You can have multiple installations in one database if you give each
 * a unique prefix. Only numbers, letters, and underscores please!
 *
 * At the installation time, database tables are created with the specified prefix.
 * Changing this value after WordPress is installed will make your site think
 * it has not been installed.
 *
 * @link https://developer.wordpress.org/advanced-administration/wordpress/wp-config/#table-prefix
 */
$table_prefix = 'tctx_';

/**
 * For developers: WordPress debugging mode.
 *
 * Change this to true to enable the display of notices during development.
 * It is strongly recommended that plugin and theme developers use WP_DEBUG
 * in their development environments.
 *
 * For information on other constants that can be used for debugging,
 * visit the documentation.
 *
 * @link https://developer.wordpress.org/advanced-administration/debug/debug-wordpress/
 */
define( 'WP_DEBUG', false );

/* Add any custom values between this line and the "stop editing" line. */



/* That's all, stop editing! Happy publishing. */

/** Absolute path to the WordPress directory. */
if ( ! defined( 'ABSPATH' ) ) {
	define( 'ABSPATH', __DIR__ . '/' );
}

/** Sets up WordPress vars and included files. */
require_once ABSPATH . 'wp-settings.php';
